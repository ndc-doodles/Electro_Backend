from rest_framework import serializers
from .models import *
from django.conf import settings
from cloudinary.utils import cloudinary_url

class ProductCategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()  # Convert public_id to full URL

    class Meta:
        model = Product_Category
        fields = ['category_name', 'image']

    def get_image(self, obj):
        if obj.image:
            return cloudinary.CloudinaryImage(str(obj.image)).build_url()
        return None  # Return None if no image is available

class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product_list
        fields = '__all__'


class Register_custumerSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['username', 'password', 'profile_image', 'discount_individual', 'search_history', 'phone_number', 'status', 'address']

    def get_profile_image(self, obj):
        if obj.profile_image:  
            return cloudinary.utils.cloudinary_url(str(obj.profile_image))[0]  # Convert public_id to full URL
        return None

class LoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = Login
        fields = '__all__'


class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart_items
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order_products
        fields = '__all__'


class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = '__all__'

class Slider_Add_Serializer(serializers.ModelSerializer):
    slider_image = serializers.SerializerMethodField()

    class Meta:
        model = Slider_Add
        fields = ['slider_image']

    def get_slider_image(self, obj):
        return str(obj.slider_image)
    

   