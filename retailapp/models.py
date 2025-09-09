
from django.db import models
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.hashers import check_password
from cloudinary.models import CloudinaryField
import cloudinary.uploader
from django.contrib.auth.models import AbstractUser
# Create your models here.

class Customer(models.Model):
    username = models.CharField(max_length=30, unique=True)
    password = models.CharField(max_length=128,blank=True)  # Increased length for hashed passwords
    profile_image = CloudinaryField('image', folder="customerprofile/",blank=True, null=True , default ="https://res.cloudinary.com/djedeaw0l/image/upload/v1744019579/customerprofile/w7kmmmmsibzmn5lfu1qx.jpg")
    discount_individual = models.CharField(max_length=20, blank=True)
    search_history = models.JSONField(default=list, blank=True)
    phone_number = models.CharField(max_length=10, blank=True)
    status = models.BooleanField(default=False)
    address = models.JSONField(default=dict,blank=True)

    @property
    def is_authenticated(self):
        return True

    def save(self, *args, **kwargs):
        # Hash the password before saving
        if not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def add_search_term(self, term):
        if not isinstance(term, str):
            raise ValidationError("Search term must be a string.")
        # Ensure search_history is a list
        if not isinstance(self.search_history, list):
            self.search_history = []
        if term not in self.search_history:  # Check for duplicates
            self.search_history.append(term)
            if len(self.search_history) > 2:  # Limit to 5 terms
                self.search_history.pop(0)  # Remove the oldest term
        self.save()

    def __str__(self):
        return self.username



class Administrator(models.Model):
    username = models.CharField(max_length=200)
    password = models.CharField(max_length=200)

    @property
    def is_authenticated(self):
        return True

    def save(self, *args, **kwargs):
    # Hash the password before saving
        if not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    def __str__(self):
        return self.username


class Login(models.Model):
    username = models.CharField(max_length=30)
    password = models.CharField(max_length=80)

    def __str__(self):
        return self.username


class Product_Category(models.Model):
    category_name = models.CharField(max_length=20)
    image =  CloudinaryField('image', folder="product_category/",blank=True, null=True) 

    @property
    def is_authenticated(self):
        return True
    
    def __str__(self):
        return self.category_name
    
class Product_list(models.Model):
    product_name = models.CharField(max_length=50)
    product_images = models.JSONField(default=list) # Stores array of strings (URLs or image paths)
    product_description = models.TextField()
    product_discount = models.CharField(max_length=20,blank=True)
    product_offer = models.CharField(max_length=20,blank=True)
    product_category = models.CharField(max_length=50)
    prize_range = models.JSONField(default=list)
    product_stock = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    @property
    def is_authenticated(self):
        return True

    def add_prize_range(self, prize):
        if not isinstance(prize, dict):
            raise ValidationError("prize must be a dictionary with key-value pairs.")
        if not isinstance(self.prize_range, list):
            self.prize_range = []

        self.prize_range.append(prize)

        if len(self.prize_range) > 3:  # Limit to 3 entries
            raise ValidationError("Only 3 entries are allowed in prize_range.")
        self.save()


class Cart_items(models.Model):
    user_id = models.CharField(max_length=10)
    products = models.JSONField(default=list)

    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return self.user_id


class Order_products(models.Model):
    user_id = models.CharField(max_length=20)
    product_items = models.JSONField(default=dict)

    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return self.user_id


class Enquiry(models.Model):
    user_id = models.CharField(max_length=20)
    product_id = models.CharField(max_length=10)
    message = models.TextField()

    @property
    def is_authenticated(self):
        return True


class Slider_Add(models.Model):
    slider_image = CloudinaryField('image', folder="slider_images/")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    @property
    def is_authenticated(self):
        return True

