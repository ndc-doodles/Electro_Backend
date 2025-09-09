from django.shortcuts import render,redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage

from rest_framework import status
from .models import *
from .serializers import *
from django.db.models import Q
from django.core.files.uploadedfile import UploadedFile
import json
from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
import jwt
import datetime
from django.contrib.auth.hashers import check_password
import base64
from cloudinary.uploader import upload
import cloudinary.uploader
from cloudinary.exceptions import Error
import random
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
import logging

SECRET_KEY = "django-insecure-+k#qrwj!@v*ls7(*xs%8!0wfip@6g^e!v!rn&d5y5d7tuj4vm(" 

class Register_admin(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if Administrator.objects.filter(username=username).exists():
            return Response({"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)

        # Create new customer with hashed password
        Admin = Administrator(username=username, password=make_password(password))
        Admin.save()

        return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)


class Register_custumer(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customers = Customer.objects.all()
        if not customers.exists():
            return Response({"message": "No customers found"}, status=status.HTTP_204_NO_CONTENT)
        
        serializer = Register_custumerSerializer(customers, many=True)
        
        # Ensure each customer entry includes its `id`
        for customer_data, customer in zip(serializer.data, customers):
            customer_data["id"] = customer.id  # Attach the `id` field

        return Response(serializer.data, status=status.HTTP_200_OK)
    

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        discount = request.data.get("discount_individual")

        if not username or not password:
            return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if Customer.objects.filter(username=username).exists():
            return Response({"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)

        # Create new customer with hashed password
        customer = Customer(username=username, password=make_password(password),discount_individual=discount)
        customer.save()

        return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)

class UpdateRegister(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        username = request.data.get("username")
        password = request.data.get("password")
        discount = request.data.get("discount_individual")

        try:
            customer = Customer.objects.get(id=id)
        except Customer.DoesNotExist:
            return Response({'error': 'The customer with this ID was not found'}, status=404)

        if username:
            customer.username = username
        if password:
            customer.set_password(password)  # Securely update the password
        if discount is not None:
            customer.discount_individual = discount

        customer.save()
        return Response({'message': 'The customer has been updated successfully'}, status=200)
        

class UserLoginView(APIView):
    permission_classes = []  # No authentication required for login

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = None
        user_type = None

        # Try fetching from Customer first
        try:
            user = Customer.objects.get(username=username)
            user_type = "customer"
        except Customer.DoesNotExist:
            # Try Administrator next
            try:
                user = Administrator.objects.get(username=username)
                user_type = "admin"
            except Administrator.DoesNotExist:
                return Response({"error": "Invalid username or password"}, status=status.HTTP_404_NOT_FOUND)

        # Check password
        if not check_password(password, user.password):
            return Response({"error": "Invalid credentials"}, status=400)

        # Generate JWT tokens manually
        tokens = get_tokens_for_user(user)

        response_data = {
            "message": "Login successful",
            "access_token": tokens["access"],
            "refresh_token": tokens["refresh"],
            "user_id": user.id,
            "username": user.username,
            "user_type": user_type,
        }

        if user_type == "customer":
            response_data["profile_image"] = user.profile_image.url if user.profile_image else None

        return Response(response_data, status=status.HTTP_200_OK)



def get_tokens_for_user(user):
    """Manually generate JWT tokens for custom user models."""
    refresh = RefreshToken()
    refresh["user_id"] = user.id
    refresh["username"] = user.username
    refresh["user_type"] = "customer" if isinstance(user, Customer) else "admin"
    
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


logger = logging.getLogger(__name__)

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.debug(f"Received request data: {request.data}")  # Debug log
        refresh_token = request.data.get("refresh")
        print("the requested token is",request.data)

        if not refresh_token:
            logger.error("No refresh token found in the request body.")
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Validate the refresh token
            refresh = RefreshToken(refresh_token)
            
            # Log the decoded refresh token for debugging
            logger.debug(f"Decoded Refresh Token: {refresh}")

            # Get the user ID and user type from the payload (the refresh token contains it)
            user_id = refresh["user_id"]
            user_type = refresh["user_type"]
            
            # Log user info
            logger.debug(f"User ID: {user_id}, User Type: {user_type}")

            # Fetch the user based on user type (Customer or Administrator)
            if user_type == "customer":
                user = Customer.objects.get(id=user_id)
            elif user_type == "admin":
                user = Administrator.objects.get(id=user_id)
            else:
                return Response({"error": "Invalid user type in token."}, status=status.HTTP_400_BAD_REQUEST)

            # Generate new tokens for the user
            tokens = get_tokens_for_user(user)

            return Response({
                "message": "Tokens refreshed successfully",
                "access_token": tokens["access"],
                "refresh_token": tokens["refresh"],
                "user_id": user.id,
                "username": user.username,
                "user_type": user_type,
            }, status=status.HTTP_200_OK)

        except TokenError:
            return Response({"error": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)

        except Customer.DoesNotExist:
            logger.error(f"Customer with ID {user_id} not found.")
            return Response({"error": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Administrator.DoesNotExist:
            logger.error(f"Administrator with ID {user_id} not found.")
            return Response({"error": "Administrator not found."}, status=status.HTTP_404_NOT_FOUND)



class ProductCategoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request,id=None):
        categories = Product_Category.objects.all()
        serializer = ProductCategorySerializer(categories, many=True)
        for categories_data, categories in zip(serializer.data, categories):
            categories_data["id"] = categories.id  # Attach the `id` field
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        name = request.data.get('name')
        image = request.FILES.get('image')

        if image and name:
            try:
                # Upload image to Cloudinary
                upload_result = cloudinary.uploader.upload(image, folder="product_category/")
                Product_Category.objects.create(category_name=name,image=upload_result['public_id'])
                return Response({'message':'the product category created'}, status=201)
            except Exception as e:
                return Response({'error': f'Upload failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({'error': 'the fields are compulsory'}, status=404)

    
class Product_categoryUpdate(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, id):
        image = request.FILES.get("image")

        # Check if category exists
        try:
            category = Product_Category.objects.get(id=id)
        except Product_Category.DoesNotExist:
            return Response({"message": "No Product_Category found"}, status=404)

        # Upload new image if provided
        cloudinary_url = None

        if image and category.image:
            try:
                cloudinary.uploader.destroy(category.image.public_id)  # Delete old image
            except Exception as e:
                return Response({"error": f"Failed to delete old image from Cloudinary: {str(e)}"}, status=500)


        if image:
            try:
                cloudinary_response = cloudinary.uploader.upload(image)
                cloudinary_url = cloudinary_response["public_id"]
            except Exception as e:
                return Response({"error": f"Cloudinary upload failed: {str(e)}"}, status=500)

        # Prepare serializer data
        updated_data = request.data.copy()
        if cloudinary_url:
            updated_data["image"] = cloudinary_url  # Update image field in data

        serializer = ProductCategorySerializer(category, data=updated_data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Product category updated successfully", "data": serializer.data}, status=200)
        else:
            return Response(serializer.errors, status=400)

        
    def delete(self, request, id):
        try:
            category = Product_Category.objects.get(id=id)
        except Product_Category.DoesNotExist:
            return Response({"message": "No Product_Category found"}, status=404)

        # Delete the image from Cloudinary if it exists
        if category.image:
            try:
                cloudinary.uploader.destroy(category.image.public_id)  # Delete from Cloudinary
            except Exception as e:
                return Response({"error": f"Failed to delete image from Cloudinary: {str(e)}"}, status=500)

        # Delete the category from database
        category.delete()

        return Response({"message": "Product category deleted successfully"}, status=200)





class ProductListPost(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        products = Product_list.objects.all()
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

    

    def post(self, request):
        product_data = request.data  

        # Ensure request data is not empty
        if not product_data:
            return Response({"error": "No data provided. Please include product details."}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(product_data, dict):
            return Response({"error": "Invalid format. Expected a dictionary."}, status=status.HTTP_400_BAD_REQUEST)

        # Extract and validate product details
        prize_list = product_data.get('prize_range')
        image_list = request.FILES.getlist("product_images")

        # Check if required fields are present
        required_fields = ["product_name", "product_category", "product_stock"]
        for field in required_fields:
            if field not in product_data or not product_data[field]:
                return Response({"error": f"'{field}' is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not image_list:
            return Response({"error": "At least one product image is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Image upload to Cloudinary
        image_urls = []
        try:
            for image in image_list[:5]:  # Limit to 5 images
                upload_result = cloudinary.uploader.upload(image)
                image_urls.append(upload_result["secure_url"])  # Store Cloudinary URL

        except Exception as e:
            return Response({"error": f"Image upload failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Validate prize_range (should be a list of up to 3 dictionaries)
        if prize_list:
            if isinstance(prize_list, str):  # In case prize_range is a stringified JSON
                try:
                    prize_list = json.loads(prize_list)  # Deserialize stringified JSON
                except json.JSONDecodeError:
                    return Response({"error": "Invalid format for prize_range. It should be a valid JSON array."}, status=status.HTTP_400_BAD_REQUEST)

            if not isinstance(prize_list, list):
                return Response({"error": "prize_range must be a list of dictionaries."}, status=status.HTTP_400_BAD_REQUEST)

            # if len(prize_list) > 3:
            #     return Response({"error": "Only up to 3 prize ranges are allowed."}, status=status.HTTP_400_BAD_REQUEST)

            for prize in prize_list:
                if not isinstance(prize, dict):
                    return Response({"error": "Each entry in prize_range must be a dictionary."}, status=status.HTTP_400_BAD_REQUEST)
                # new_entry = {
                #         "from": prize.get("from", ""),  # Default empty if not provided
                #         "to": prize.get("to", ""),
                #         "prize": prize.get("prize", ""),
                #         "id": prize.get(id, "")

                #     }
                # prize_list.append(new_entry)

        else:
            prize_list = []  # If prize_range is not provided, set it to an empty list

        # Create Product Instance
        try:
            product = Product_list.objects.create(
                product_name=product_data["product_name"],
                product_images=image_urls,  # Store uploaded image URLs
                product_description=product_data.get("product_description", ""),
                product_discount=product_data.get("product_discount", "0%"),
                product_offer=product_data.get("product_offer", ""),
                product_category=product_data["product_category"],
                prize_range=prize_list,
                product_stock=product_data["product_stock"]
            )

            # Serialize the product data
            serializer = ProductListSerializer(product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({"error": f"Product creation failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class ProduclistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
            response_data = []
            products = Product_list.objects.all()

            for product in products:
                product_prize = product.prize_range
                print("product_prize is", product_prize)

                try:
                    discount = int(product.product_discount)
                    print('product_discount is:', discount)
                except (ValueError, TypeError):
                    discount = 0  # Default discount is 0 if not valid

                discounted_prices = []
                for prize in product_prize:
                    if 'price' in prize:
                        try:
                            actual_prize = int(prize['price'])
                            print("actual_prize is", actual_prize)

                            final_discount = actual_prize - (actual_prize * discount / 100)
                            print("Final Price after Discount:", final_discount)

                            discounted_prices.append({
                                "actual_price": actual_prize,
                                "final_discount": final_discount
                            })
                            print("The output array is", discounted_prices)
                            
                        except (ValueError, TypeError):
                            continue  # Skip invalid prices

                # Serialize the product data
                serializer = ProductListSerializer(product)
                product_data = serializer.data
                product_data['discounted_prices'] = discounted_prices  # Add discount data
                response_data.append(product_data)

            # Ensure a valid Response is always returned
            return Response(response_data, status=status.HTTP_200_OK)
    

class ProduclistViewlimit(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
            response_data = []
            products = Product_list.objects.all()[:6]

            for product in products:
                product_prize = product.prize_range
                print("product_prize is", product_prize)

                try:
                    discount = int(product.product_discount)
                    print('product_discount is:', discount)
                except (ValueError, TypeError):
                    discount = 0  # Default discount is 0 if not valid

                discounted_prices = []
                for prize in product_prize:
                    if 'price' in prize:
                        try:
                            actual_prize = int(prize['price'])
                            print("actual_prize is", actual_prize)

                            final_discount = actual_prize - (actual_prize * discount / 100)
                            print("Final Price after Discount:", final_discount)

                            discounted_prices.append({
                                "actual_price": actual_prize,
                                "final_discount": final_discount
                            })
                            print("The output array is", discounted_prices)
                            
                        except (ValueError, TypeError):
                            continue  # Skip invalid prices

                # Serialize the product data
                serializer = ProductListSerializer(product)
                product_data = serializer.data
                product_data['discounted_prices'] = discounted_prices  # Add discount data
                response_data.append(product_data)

            # Ensure a valid Response is always returned
            return Response(response_data, status=status.HTTP_200_OK)




class Product_updateanddelete(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request,id):
        try:
            product = Product_list.objects.get(id = id)
            serializer = ProductListSerializer(product)
            return Response(serializer.data,status=200)
        except:
            return Response({"error": "Product not found"}, status=404)



    def patch(self, request, id):
        item = get_object_or_404(Product_list, id=id)
        new_images = request.FILES.getlist("new_product_images")  # Use getlist to get multiple files
        existing_images_update = request.data.get('existing_images_update', [])
        print("the new_images is",new_images)


        # Extract fields from request
        # item_no = request.data.get("item_number")
        # new_image = request.FILES.get("new_image")
        new_range = request.data.get("prize_range", [])  # Default to empty list

        # Ensure new_range is properly formatted (list or JSON string)
        if isinstance(new_range, str):
            try:
                new_range = json.loads(new_range)  # Convert JSON string to list
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid JSON format for prize_range."}, 
                    status=400
                )

        if not isinstance(new_range, list):
            return Response({"error": "prize_range must be a list."}, status=400)

        # Ensure existing prize_range is a list
        existing_prize_range = item.prize_range if isinstance(item.prize_range, list) else []

        # Convert existing prize range into a dictionary (id -> entry) for fast lookups
        existing_prize_dict = {str(entry.get("id")): entry for entry in existing_prize_range if "id" in entry}

        # Validate and process new_range updates
        for entry in new_range:
            entry_id = str(entry.get("id")) if entry.get("id") is not None else None

            if entry_id and entry_id in existing_prize_dict:
                # Update existing entry
                existing_entry = existing_prize_dict[entry_id]
                existing_entry["from"] = entry.get("from", existing_entry.get("from", ""))
                existing_entry["to"] = entry.get("to", existing_entry.get("to", ""))
                existing_entry["rate"] = entry.get("rate", existing_entry.get("rate", ""))
            else:
                
                # Add new entry to the list
                new_entry = {
                    "id": entry.get("id", ""),
                    "from": entry.get("from", ""),
                    "to": entry.get("to", ""),
                    "rate": entry.get("rate", ""),
                }
                existing_prize_range.append(new_entry)

        # Save updated prize_range
        item.prize_range = existing_prize_range
        # item.save()

        # Update image if provided
        if not isinstance(item.product_images, list):
            item.product_images = []  # Ensure it's a list
        
        try:
            existing_images_update = json.loads(existing_images_update) if isinstance(existing_images_update, str) else existing_images_update
            if not isinstance(existing_images_update, list):
                existing_images_update = []
        except Exception:
            existing_images_update = []

        # STEP 1: Find deleted images
        previous_images = set(item.product_images)
        updated_images_set = set(existing_images_update)
        deleted_images = previous_images - updated_images_set

        # STEP 2: Delete removed images from Cloudinary
        for public in deleted_images:
            try:
                # Split the URL and get the last part
                public_id_with_ext = public.split('/')[-1]
                public_id = public_id_with_ext.rsplit('.', 1)[0]  # Remove file extension

                # Delete from Cloudinary
                cloudinary.uploader.destroy(public_id)
                print(f"Deleted: {public_id}")
            except Exception as e:
                print(f"Failed to delete image from Cloudinary: {e}")

        uploaded_images = []
        existing_images_update = list(existing_images_update)
        for image in new_images:
            print("the single image is",image)
            try:
                cloudinary_response = cloudinary.uploader.upload(image)
                uploaded_images.append(cloudinary_response["secure_url"])  # Store new Cloudinary URLs

            except Exception as e:
                return Response({"error": f"Cloudinary upload failed: {str(e)}"}, status=500)

        # Combine existing images with new images
        
        updated_images = existing_images_update + uploaded_images

        print("the updated_images is",updated_images)

        # Keep only the first 5 images (remove extras)
        if len(updated_images) > 5:
            removed_images = updated_images[5:]  # Get images that are removed
            updated_images = updated_images[:5]  # Keep only first 5

            item.product_images = updated_images
            item.save()

            return Response({
                'message': f'Images added successfully, but {len(removed_images)} extra images were discarded.',
                'final_images': updated_images,
                'removed_images': removed_images
            }, status=status.HTTP_200_OK)
        item.product_images = updated_images
        item.save()

        # Dynamically update other fields in the request
        mutable_data = request.data.dict()
        mutable_data.pop("prize_range", None)


        serializer = ProductListSerializer(item, data=mutable_data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Product updated successfully", "data": serializer.data}, status=200)
        else:
            return Response(serializer.errors, status=400)

            
    def delete(self,request,id):
        try:
            product = Product_list.objects.get(id=id)
        except Product_list.DoesNotExist:
            return Response({'error':'the product not found'},status=400)
        
        if product.product_images:
            try:
                for url in product.product_images:
                    public_id = url.split("/")[-1].split(".")[0]  # crude but works
                    cloudinary.uploader.destroy(public_id)
            except Exception as e:
                return Response({"error": f"Failed to delete image: {str(e)}"}, status=500)
        
        if product:
            product.delete()
            return Response({'message':'the product deleted '},status=200)

    def post(self, request, id):
        index = request.data.get('id')
        
        try:
            product = Product_list.objects.get(id=id)
        except Product_list.DoesNotExist:
            return Response({'message': 'The product was not found'}, status=404)

        # Convert index to integer for comparison
        try:
            index = int(index)
        except (ValueError, TypeError):
            return Response({'message': 'Invalid ID format'}, status=400)

        # Remove the entry with matching id
        updated_prize_range = [prize for prize in product.prize_range if int(prize.get('id', -1)) != index]

        # Update the product with the new prize_range
        product.prize_range = updated_prize_range

        product.save()
        
        return Response({'message': 'Prize entry deleted successfully', 'updated_prize_range': product.data}, status=200)


               

class ProductAddExtraImage(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        new_images = request.FILES.get("new_product_images")  # Get multiple uploaded files
        print("Received images:", new_images)

        product = Product_list.objects.filter(id=id).first()
        if not product:
            return Response({'message': 'No product found'}, status=status.HTTP_404_NOT_FOUND)

        if not new_images:
            return Response({'message': 'At least one new image is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(product.product_images, list):
            product.product_images = []  # Ensure it's a list

        uploaded_images = []
        for image in new_images:
            try:
                cloudinary_response = cloudinary.uploader.upload(image)
                cloudinary_url = cloudinary_response.get("secure_url")

                if not cloudinary_url:
                    return Response({"error": "Failed to upload image to Cloudinary"}, status=500)

                uploaded_images.append(cloudinary_url)  # Store new Cloudinary URLs

            except Exception as e:
                return Response({"error": f"Cloudinary upload failed: {str(e)}"}, status=500)

        # Combine existing images with new images
        updated_images = product.product_images + uploaded_images

        # Keep only the first 5 images (remove extras)
        if len(updated_images) > 5:
            removed_images = updated_images[5:]  # Get images that are removed
            updated_images = updated_images[:5]  # Keep only first 5

            product.product_images = updated_images
            product.save()

            return Response({
                'message': f'Images added successfully, but {len(removed_images)} extra images were discarded.',
                'final_images': updated_images,
                'removed_images': removed_images
            }, status=status.HTTP_200_OK)

        # Save updated images if under the limit
        product.product_images = updated_images
        product.save()

        return Response({
            'message': 'Images added successfully',
            'final_images': updated_images
        }, status=status.HTTP_200_OK)
        

    # def delete(self,request,id):
    #     index= request.data.get("index")
    #     if index:
    #         index = int(index)
    #         print("the index is:",index)
    #     try:
    #         product = Product_list.objects.get(id=id)
    #         print("the product is:",product)
    #         if product:
    #             image_list = product.product_images
    #             print("the image_list is:",image_list)
    #             if isinstance(image_list, list) and 0 <= index < len(image_list):
    #                 deleted_image  = image_list.pop(index)  # Get image at the specified index
    #                 product.product_images = image_list  # Update the field
    #                 product.save()  # Save changes to the database
    #                 print("Deleted Image URL:", deleted_image)
    #                 serializer = ProductListSerializer(product)
    #                 return Response(serializer.data)
    #             else:
    #                 return Response({"error": "no image_list found"}, status=500)
    #     except Exception as e:
    #         return Response({"error": "no product found"}, status=500)

    # def post(self, request, id):
    #     existing_images_update = request.data.get('existing_images_update', [])

    #     if not isinstance(existing_images_update, list):
    #         return Response({'error': 'The existing_images_update must be a list'}, status=400)

    #     # Fetch the product
    #     product = get_object_or_404(Product_list, id=id)

    #     # Ensure product_images is a list
    #     if not isinstance(product.product_images, list):
    #         return Response({'error': 'product_images field is not a list'}, status=400)

    #     # Update the images
    #     product.product_images = existing_images_update

    #     # Save the product
    #     product.save()

    #     return Response({'message': 'Product images updated successfully'}, status=200)



# storing the search history

class Search_history(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if the user is logged in
        user_id = request.data.get("user_id")  # Assuming "author" stores the logged-in user's ID
        print('user is',user_id)
        if user_id:
            try:
                # Fetch the user from the database
                user = Customer.objects.get(id=user_id)
            except Customer.DoesNotExist:
                return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

            # Get the search history from the request
            term = request.data.get('term')
            print("the term is",term)

            if not term:
                return Response({"error": "Search term is required"}, status=status.HTTP_400_BAD_REQUEST)
            user.add_search_term(term)
            serializer = Register_custumerSerializer(user)
            print("the append data is",user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'No user_id provided'}, status=status.HTTP_404_NOT_FOUND)
        
    
    def get(self, request):
        user_id = request.query_params.get("user_id")  # Get the user ID from query params
        see_more = request.query_params.get("see_more", "false").lower() == "true"  # Check if 'see more' is clicked

        print('get user is', user_id)
        
        if user_id:
            try:
                # Fetch the user from the database
                user = Customer.objects.get(id=user_id)
                search_data = user.search_history  # ["Footwear", "Watches"]
                print('the user search history:', search_data)

                if not search_data:
                    try:
                        all_products = list(Product_list.objects.all())
                    except Product_list.DoesNotExist:
                        return Response({'error': 'Product_list DoesNotExist.'}, status=400)

                    if len(all_products) >= 1:
                        products_list = random.sample(all_products, k=1)
                        serializer = ProductListSerializer(products_list, many=True)
                        return Response(serializer.data, status=200)
                    else:
                        return Response({'error': 'Not enough products to sample from.'}, status=400)


                # Fetch products that match search_data
                matched_products = list(Product_list.objects.filter(product_category__in=search_data))

                if not matched_products:
                    return Response({'message': 'No matching products found'}, status=status.HTTP_204_NO_CONTENT)

                # Shuffle the matched products to mix their order
                random.shuffle(matched_products)

                # If 'see_more' is clicked, return all products, otherwise, return only 6
                if not see_more:
                    matched_products = matched_products[:6]

                # Serialize and return the response
                serializer = ProductListSerializer(matched_products, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

            except Customer.DoesNotExist:
                return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'message': 'user_id is compulsory'}, status=status.HTTP_400_BAD_REQUEST)


# view for new arrivals
class Newly_arrived(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch the 5 most recently added products
        products = Product_list.objects.order_by('-created_at')[:6]  # Ensure 'created_at' field exists in your model

        # Serialize the products
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class Home(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        content = {'message': 'Hello, World!'}
        return Response(content)


# profile update
class Profile_update_custumer(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id):
        try:
            customer = Customer.objects.get(id=id)
            serializer = Register_custumerSerializer(customer)
            response_data = serializer.data
            response_data["id"] = id  # Attach the ID to the response
            return Response(response_data, status=200)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found", "id": id}, status=400)


    def patch(self, request, id):
        try:
            customer = Customer.objects.get(id=id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get the request data
        request_data = request.data.copy()

        # Handle Address Update Separately (if provided)
        new_address = request_data.pop('address', None)
        new_image = request.FILES.get('image', None)

        if new_address:
            if not isinstance(new_address, dict):
                return Response({'error': 'Address must be a dictionary'}, status=status.HTTP_400_BAD_REQUEST)

            # Ensure existing address is a dictionary
            try:
                existing_address = json.loads(customer.address) if isinstance(customer.address, str) else customer.address
            except json.JSONDecodeError:
                existing_address = {}

            # Merge new address into existing address
            existing_address.update(new_address)

            # Save the updated address
            customer.address = existing_address
            customer.save()
        if new_image and customer.profile_image:
            try:
                cloudinary.uploader.destroy(customer.profile_image.public_id)
            except Exception as e:
                return Response({"error": f"Failed to delete old image from Cloudinary: {str(e)}"}, status=500)
            
        if new_image:
            try:
                # Upload image to Cloudinary
                upload_result = cloudinary.uploader.upload(new_image, folder="customerprofile/")

                # Replace old image with new public_id
                customer.profile_image = upload_result["public_id"]
                customer.save()

            except Exception as e:
                return Response({'error': f'Upload failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        # Proceed with updating other fields if needed
        serializer = Register_custumerSerializer(customer, data=request_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


    def delete(self,request,id):
        customer = Customer.objects.get(id=id)
        if customer:
            customer.delete()
            return Response({"message": "Customer deleted"}, status=200)
        else:
            return Response({"error": "Customer not found"}, status=400)
        

    def post(self, request, id):
        try:
            customer = Customer.objects.get(id=id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=400)

        if customer.profile_image:
            try:
                cloudinary.uploader.destroy(customer.profile_image.public_id)
                # Set image field to None (or default image if needed)
                customer.profile_image = None  # or set to 'path/to/default/image' if default isn't applied automatically
                customer.save()
            except Exception as e:
                return Response({"error": f"Failed to delete old image from Cloudinary: {str(e)}"}, status=500)

        return Response({"message": "Profile image removed, default image set."}, status=200)


# category filtering homescreen
class Category_filter(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
            category = request.data.get('category_name')
            print('Category received:', category)

            check = Product_list.objects.filter(product_category=category)

            if check.exists():  # Check if queryset is not empty
                print('Matching categories:', check)
                serializer = ProductListSerializer(check, many=True)  # Add many=True
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

class Adding_cart(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        products = request.data.get('products')

        print("Received user_id:", user_id)
        print("Received products:", products)

        # Validate data
        if user_id is None:
            return Response({"error": "Invalid data format (user_id missing or products is not a list)"}, status=status.HTTP_400_BAD_REQUEST)
        
        if isinstance(products, dict):
            products = [products]
        elif not isinstance(products, list):
            return Response({"error": "products must be a list or a product object"}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the user's cart
        try:
            cart = Cart_items.objects.filter(user_id=user_id).first()
        except Cart_items.DoesNotExist:
            cart=None
        
        if cart:
            if not isinstance(cart.products, list):
                cart.products = list(cart.products)
                print("the cart items is",cart)
                print("Type of cart.products:",cart.products)
            # Update the existing cart
            existing_products = {item["id"]: item for item in cart.products}  # Create a dictionary for quick lookup
            print('the existing_products',existing_products)

            for new_product in products:
                product_id = new_product.get("id")
                new_count = int(new_product.get("count", 1))  # Ensure new count is an integer

                if product_id in existing_products:
                    # Convert existing count to integer before addition
                    existing_products[product_id]["count"] = int(existing_products[product_id].get("count", 1)) + new_count
                else:
                    # Ensure count is stored as an integer
                    new_product["count"] = new_count
                    existing_products[product_id] = new_product

            # Update cart products
            cart.products = list(existing_products.values())
            cart.save()
        else:
            # If no cart exists, create a new one and ensure count is stored as an integer
            # for product in products:
                # product["count"] = int(product.get("count", 1))
            cart = Cart_items.objects.create(user_id=user_id, products=products)

        # Serialize and return response
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

    def get(self, request):
        user = request.query_params.get('userid')
        print('Current author is:', user)
        try:
            user_cart_items = Cart_items.objects.filter(user_id=user).first()
            print('User cart items:', user_cart_items)

        except Cart_items.DoesNotExist:
            return Response({"error": "No matching cart items found"}, status=404)

        cart_data = []

        # for item in user_cart_items:
        #     print("Processing Cart Item:", item)
            # print("Item Products Data:", item.products)

        for product in user_cart_items.products:  
            print('the product iterator is',product)
            p_id = product["id"]
            print('the p_id is',p_id)

            product_count = int(product.get('count', 0))  
            print("Extracted Product ID:", p_id, "Product Count:", product_count)

            if not p_id:
                continue  

            # Fetch product details
            product_obj = Product_list.objects.filter(id=p_id).first()
            print("Fetched Product Object:", product_obj)

            if product_obj is None:
                continue

            # Get customer details and individual discount
            invidual = Customer.objects.filter(id=user).first()
            # discount_individual = int(invidual.discount_individual)
            individual_discount = float(invidual.discount_individual.strip().replace("%", "")) / 100 if invidual and invidual.discount_individual else 0

            print("Individual Discount:", individual_discount)

            # Get product discount
            # product_discount = int(product_obj.product_discount)                
            product_discount = float(product_obj.product_discount.strip().replace("%", "")) / 100 if product_obj and product_obj.product_discount else 0
            print("Product Discount:", product_discount)

            # Calculate total amount
            total_amount = 0
            if product_obj and product_obj.prize_range:
                for prize in product_obj.prize_range:
                    start = int(prize.get('from', 0) or 0)
                    end = int(prize.get('to', 0) or 0)
                    price = float(prize.get('rate', 0) or 0)

                    print(f"Checking range: from {start} to {end}, prize: {price}")

                    if start <= product_count <= end:
                        discount_to_apply = product_discount if product_discount else 0
                        discounted_price = price * (1 - discount_to_apply)
                        total_amount = product_count * discounted_price
                        print("Total Amount for Product:", total_amount)
                        break  

            # Append product details to cart_data
            if product_obj:
                cart_data.append({
                    "user_id": user_cart_items.user_id,
                    "username":invidual.username,
                    "product_id":p_id,
                    "total_count": product_count,
                    "product_name": product_obj.product_name,
                    "product_images": product_obj.product_images if product_obj.product_images else None,
                    "product_description": product_obj.product_description,
                    "product_discount": product_obj.product_discount,
                    "individual_discount": individual_discount,
                    "product_offer": product_obj.product_offer,
                    "product_category": product_obj.product_category,
                    "prize_range": product_obj.prize_range,
                    "product_stock": product_obj.product_stock,
                    "total_amount": total_amount,
                })

                sum_total = sum(item['total_amount'] for item in cart_data)
                print("Total before discount:", sum_total)

                discount_to_user = individual_discount if individual_discount else 0
                discount_amount = sum_total * discount_to_user  # Calculate discount amount
                final_price = sum_total - discount_amount  # Subtract discount from total

                response_data = {
                    "cart_data": cart_data,
                    "sum_total": sum_total,  # Total before discount
                    "discount_amount": discount_amount,  # Discount applied
                    "final_price": final_price  # Total after discount
                }

                print("Discount applied:", discount_amount)
                print("Final total after discount:", final_price)
                

        if not cart_data:
            return Response({"error": "No products found in cart"}, status=400)

        return Response(response_data) 


class Count_order_update(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        count = request.data.get('count')
        product_id = request.data.get('product_id')
        user_id = request.data.get("user_id")

        print("Received request data:", count, product_id, user_id)

        # Validate request data
        if None in (count, product_id, user_id):
            return Response({"error": "Missing count, product_id, or user_id"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the cart for the given user
        cart = Cart_items.objects.filter(user_id=user_id).first()

        if not cart:
            return Response({"error": "Cart not found for the user"}, status=status.HTTP_404_NOT_FOUND)

        print("Cart Items before update:", cart.products)

        # Update the count of the product in the cart
        updated = False
        for item in cart.products:
            if str(item.get('id')) == str(product_id):  # Ensure ID comparison works
                item['count'] = int(count)  # Update the count
                updated = True
                break

        if not updated:
            return Response({"error": "Product not found in cart"}, status=status.HTTP_404_NOT_FOUND)

        # Save updated cart
        cart.save()

        print("Cart Items after update:", cart.products)

        # Serialize and return updated cart
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)




class Delete_all_cart(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        user = request.data.get('username')
        cart_items = Cart_items.objects.filter(user_id = user)
        if cart_items is not None:
            cart_items.delete()
            return Response({"message": "Cart items deleted succesfully"}, status=200)
        else:
            return Response({"error": "No items found in cart"}, status=400)
        
    def delete(self, request):
        # Extract request data
        product_id = request.data.get("id")
        user_id = request.data.get("user_id")

        if not product_id or not user_id:
            return Response({"error": "Product ID and User ID are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product_id = int(product_id)
            user_id = int(user_id)
        except ValueError:
            return Response({"error": "Invalid product ID or user ID"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the user's cart
        cart = Cart_items.objects.filter(user_id=user_id).first()

        if not cart:
            return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if the product exists in the cart
        product_found = False
        updated_products = []

        for product in cart.products:
            if product["id"] == product_id:
                product_found = True
            else:
                updated_products.append(product)  # Keep other products

        if not product_found:
            return Response({"error": "Product not found in cart"}, status=status.HTTP_404_NOT_FOUND)

        # Update the cart
        cart.products = updated_products
        cart.save(update_fields=["products"])

        return Response({"message": "Product removed successfully", "updated_cart": updated_products}, status=status.HTTP_200_OK)
        


class order_products(APIView):
    permission_classes = [IsAuthenticated]

    # def post(self, request):
    #     user_id = request.data.get('userid')
    #     orders = request.data.get('orders')

    #     print("Received user_id:", user_id)
    #     print("Received products:", orders)

    #     # Validate user_id and orders
    #     if not user_id or not isinstance(orders, dict):
    #         return Response({"error": "Invalid data format (user_id missing or orders is not a dict)"}, status=status.HTTP_400_BAD_REQUEST)

    #     try:
    #         # Create new order
    #         order_products = Order_products.objects.create(user_id=user_id, product_items=orders)
    #         serializer = OrderSerializer(order_products)

    #         # Clear user's cart if it exists
    #         cart = Cart_items.objects.filter(user_id=user_id).first()
    #         if cart:
    #             cart.delete()
    #             print("Cart cleared for user:", user_id)
    #             return Response({"message":"Order placed successfully and Cart cleared for user","order_details":serializer.data},status=200)
    #         return Response({
    #             "message": "Order placed successfully",
    #             "order_details": serializer.data
    #         }, status=status.HTTP_201_CREATED)

    #     except Exception as e:
    #         print(f"Error placing order: {e}")
    #         return Response({"error": "Failed to place order"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        user_id = request.data.get('userid')
        orders = request.data.get('orders')

        print("Received user_id:", user_id)
        print("Received products:", orders)

        # Validate user_id and orders
        if not user_id or not isinstance(orders, dict):
            return Response({"error": "Invalid data format (user_id missing or orders is not a dict)"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create new order
            order_products = Order_products.objects.create(user_id=user_id, product_items=orders)
            serializer = OrderSerializer(order_products)

            user = Customer.objects.filter(id=user_id).first()
            username = user.username if user else f"User ID: {user_id}"

            message_body = f"New Order placed by user: {username}\nOrder Details:\n"

            order_data = orders  # your full orders dict

            # Format address nicely
            address = order_data.get('address', {})
            message_body += "Address:\n"
            message_body += f"  House Name: {address.get('housename', '')}\n"
            message_body += f"  Road Name: {address.get('roadname', '')}\n"
            message_body += f"  Landmark: {address.get('landmark', '')}\n"
            message_body += f"  District: {address.get('district', '')}\n"
            message_body += f"  City: {address.get('city', '')}\n"
            message_body += f"  State: {address.get('state', '')}\n"
            message_body += f"  Postcode: {address.get('postcode', '')}\n\n"

            # Other main order info
            message_body += f"Order ID: {order_data.get('order_id', '')}\n"
            message_body += f"Date: {order_data.get('date', '')}\n"
            message_body += f"Final Amount: {order_data.get('final_amount', '')}\n\n"

            # Products details (list of dicts)
            products = order_data.get('products', [])
            message_body += "Products:\n"
            for i, product in enumerate(products, 1):
                product_obj = Product_list.objects.filter(id=product.get('product_id')).first()
                product_name = product_obj.product_name if product_obj else f"Product ID: {product.get('product_id')}"
                
                message_body += f"  Product {i}:\n"
                message_body += f"    Product Name: {product_name}\n"
                message_body += f"    Count: {product.get('count', '')}\n"
                message_body += f"    Total Amount: {product.get('total_amount', '')}\n\n"
                        # Now send this message_body via Twilio
            try:
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                client.messages.create(
                    from_='whatsapp:+14155238886',
                    body=message_body,
                    to='whatsapp:+918129106509'  # Admin WhatsApp number
                )
                print("WhatsApp message sent to admin.")
            except Exception as e:
                print(f"Error sending WhatsApp message: {e}")

            # Clear user's cart if it exists
            cart = Cart_items.objects.filter(user_id=user_id).first()
            if cart:
                cart.delete()
                print("Cart cleared for user:", user_id)
                return Response({"message":"Order placed successfully and Cart cleared for user","order_details":serializer.data},status=200)

            return Response({
                "message": "Order placed successfully",
                "order_details": serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Error placing order: {e}")
            return Response({"error": "Failed to place order"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def get(self, request):
        user = request.query_params.get('userid')
        print("The userid:", user)

        if not user:
            return Response({"error": "No User found"}, status=400)

        final_list = []
        try:
            customer = Customer.objects.get(id=user)

        except Customer.DoesNotExist:
            return Response({"error": "No customer found"}, status=404)

        check_order = Order_products.objects.filter(user_id=user)
        print("The order items with user:", check_order)

        if not check_order.exists():
            return Response({"error": "No product found for this user"}, status=404)

        for order in check_order:
            try:
                print(f"Raw order data for order {order.id}: {order.product_items}")  # Debugging

                order_data = order.product_items  # Get JSONField

                # If it's None, skip this order
                if order_data is None:
                    print(f"Skipping order {order.id}, product_items is None")
                    continue  

                # If it's a string, convert it to JSON
                if isinstance(order_data, str):
                    order_data = json.loads(order_data)

                # If it's a list, take the first item (assuming each order should be a dict)
                if isinstance(order_data, list):
                    if len(order_data) == 0:
                        print(f"Skipping order {order.id}, empty list in product_items")
                        continue
                    order_data = order_data[0]  # Take the first dictionary in the list

                if not isinstance(order_data, dict):  # Ensure it's a dictionary
                    raise ValueError(f"Expected a dictionary, got {type(order_data)}")

            except (json.JSONDecodeError, ValueError, AttributeError) as e:
                print(f"Error decoding order data for order {order.id}: {e}")
                return Response({"error": "Invalid order data"}, status=500)

            # Prepare order details
            order_list = {
                "id":order.id,
                "userid": user,
                "address": order_data.get("address"),
                "order_id": order_data.get("order_id"),
                "date": order_data.get("date"),
                "final_amount": order_data.get("final_amount"),
                "order_track":order_data.get("order_track")
            }

            product_data = []
            for product in order_data.get("products", []):  # Ensure products key exists
                product_id = product.get("product_id")
                print("The product ID is:", product_id)

                # Fetch product details
                product_list = Product_list.objects.filter(id=product_id).first()
                if not product_list:
                    print(f"Skipping product with ID {product_id} (Not Found)")
                    continue  

                product_data.append(
                    {
                        "product_id": product_id,
                        "product_name": product_list.product_name,
                        "product_images": product_list.product_images if product_list.product_images else None,
                        "product_category": product_list.product_category,
                        "product_stock": product_list.product_stock,
                        "product_description": product_list.product_description,
                        "order_status": product.get("order_status"),
                        "count": product.get("count"),
                        "total_amount":product.get("total_amount")
                    }
                )

            final_list.append({
                "order_list": order_list,
                "product_data": product_data,
            })

        if not final_list:
            return Response({"error": "No orders found"}, status=404)
        return Response(final_list)



class UpdateOrderStatus(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        order_reject = request.data.get("rejected_products", [])  # List of rejected product IDs
        user_id = request.data.get("userId")
        order_id = str(request.data.get("orderId", 0))  # Convert order_id to string
        # ordertrack = request.data.get("order_track")

        print("The request data list:", order_reject, user_id, order_id)

        # Fetch orders related to the user
        orders = Order_products.objects.filter(user_id=user_id)
        print("The order data:", orders)

        if not orders.exists():
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        rejected_product_ids = {int(pid) for pid in order_reject}
        print("Rejected product IDs:", rejected_product_ids)

        updated = False  # Flag to check if any update happens
        order_found = False  # Flag to check if at least one order_id matches
        updated_orders = []  # Store updated order items

        for order in orders:
            product_items_list = order.product_items  
            print("The product_items_list data:", product_items_list)

            id_order = str(product_items_list.get("order_id"))
            print("Checking id_order:", id_order)

            if id_order == order_id:  # Ensure order_id matches
                order_found = True
                # product_items_list['order_track'] = ordertrack  # Update tracking status

                for product in product_items_list.get("products", []):
                    proid = int(product.get("product_id", 0))  # Ensure product_id is an integer
                    print("Checking product ID:", proid)

                    if proid in rejected_product_ids:
                        print(f"Rejecting product: {proid}")
                        product["order_status"] = "Reject"
                    else:
                        product["order_status"] = "Accept"

                    updated = True

                    # Save changes if any updates were made
                if updated:
                    product_items_list['order_track'] = (
                        "Accept" if any(p["order_status"] == "Accept" for p in product_items_list["products"]) else "Reject"
                        )
                    
                    order.product_items = product_items_list
                    order.save(update_fields=["product_items"])  # Save only the modified field
                    print(f"Order {order.id} updated successfully")
                    updated_orders.append(product_items_list)

        if not order_found:
            return Response({"message": "No orders match"}, status=status.HTTP_400_BAD_REQUEST)

        if updated:
            return Response(
                {"message": "Order updated successfully", "updated_items": updated_orders},
                status=status.HTTP_200_OK
            )

        return Response({"message": "No updates were made"}, status=status.HTTP_400_BAD_REQUEST)

class Update_tracking(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        order_loc = request.data.get('order_track')  # New tracking status

        try:
            order_list = Order_products.objects.get(id=id)  # Fetch the order
        except Order_products.DoesNotExist:
            return Response({'error': 'No orders found'}, status=status.HTTP_404_NOT_FOUND)

        if not isinstance(order_list.product_items, dict):
            return Response({'error': 'Invalid product items format'}, status=status.HTTP_400_BAD_REQUEST)

        products = order_list.product_items  # Assuming this is a dictionary
        print('The products:', products)

        # Ensure 'order_track' exists in the dictionary
        if 'order_track' not in products:
            return Response({'error': "'order_track' key missing in product items"}, status=status.HTTP_400_BAD_REQUEST)

        tracking_status = ['Accept', 'Shipped', 'Packed']
        
        if products['order_track'] in tracking_status:
            products['order_track'] = order_loc  # Update tracking status
            order_list.product_items = products  # Assign updated dict
            order_list.save(update_fields=['product_items'])  # Save changes

            return Response({'message': 'Order status updated successfully', 'updated_product_items': products},
                            status=status.HTTP_200_OK)
        
        return Response({'error': 'Invalid order tracking status'}, status=status.HTTP_400_BAD_REQUEST)



class CancelOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        username = request.data.get("user_id")
        order_id = request.data.get("order_id")

        if not username or not order_id:
            return Response({"message": "Username and Order ID are required"}, status=400)

        order_id = str(order_id)  # Ensure order_id is a string for accurate comparison

        # Fetch all orders for the user
        order_list = Order_products.objects.filter(user_id=username)

        if not order_list.exists():
            return Response({"message": "Order not found"}, status=404)

        # Find the specific order containing the order_id in product_items
        order_to_delete = None

        for order in order_list:
            if order.product_items.get("order_id") == order_id:  # Ensure order_id matches

                # Check if all products have order_status = "null" or None
                all_null_status = all(
                    str(product.get("order_status", "")).lower() in ["null", "none"]
                    for product in order.product_items.get("products", [])
                )

                if all_null_status:
                    order_to_delete = order
                    break  # Stop checking further once a deletable order is found

        if not order_to_delete:
            return Response({"message": "Order cannot be cancelled or not found"}, status=400)

        order_to_delete.delete()
        return Response({"message": "Order cancelled successfully"}, status=200)


    def delete(self, request):
        userid = request.data.get("user_id")
        orderid = request.data.get("order_id")
        productid = request.data.get("product_id")  # Expecting an integer

        # Validate required fields
        if not all([userid, orderid, productid]):
            return Response(
                {"error": "All fields (user_id, order_id, product_id) are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            userid = int(userid)
            productid = int(productid)  # Ensure product_id is an integer
        except ValueError:
            return Response(
                {"error": "Invalid ID format, must be integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch orders for the user
        order_list = Order_products.objects.filter(user_id=userid)

        if not order_list.exists():
            return Response(
                {"error": "Order not found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )

        print(f"User ID: {userid}, Order ID: {orderid}, Product ID: {productid}")

        product_found = False  # Track whether product_id exists in the order

        for order_item in order_list:
            if order_item.product_items.get("order_id") == orderid:
                original_products = order_item.product_items.get("products", [])

                # Check if the product exists in the order
                for product in original_products:
                    if int(product["product_id"]) == productid:
                        product_found = True
                        # If order_status is not "null", return an error message
                        if product["order_status"] != "null":
                            return Response(
                                {"message": "Order for this product is Accepted"},
                                status=status.HTTP_400_BAD_REQUEST,  # Change to 400 to indicate an error
                            )

                if not product_found:
                    return Response(
                        {"error": "Product not found in the specified order"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Remove the product if order_status is "null"
                updated_products = [
                    product
                    for product in original_products
                    if not (int(product["product_id"]) == productid and product["order_status"] == "null")
                ]

                if updated_products:  # If products remain, update the order
                    total_amount = sum(product.get("total_amount", 0) for product in updated_products)

                    order_item.product_items["products"] = updated_products
                    order_item.product_items["final_amount"] = total_amount

                    order_item.save(update_fields=["product_items"])

                    return Response(
                        {"message": "Product removed successfully", "updated_final_amount": total_amount},
                        status=status.HTTP_200_OK,
                    )

                else:  # If no products remain, delete the order
                    order_item.delete()
                    return Response(
                        {"message": "Product removed successfully and order deleted because no items exist"},
                        status=status.HTTP_200_OK
                    )

        return Response(
            {"error": "Product not found or cannot be deleted"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    


class Stock_auto_update(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        order_list = Order_products.objects.all()
        products = Product_list.objects.all()
        updated_products = []  # Store updated products

        for product in products:
            product_id = product.id
            stock = int(product.product_stock)
            print("Product ID & Stock:", product_id, stock)

            for orders in order_list:
                for items in orders.product_items:
                    id_product = items.get('product_id')
                    order_status = items.get('order_status')

                    if str(id_product) == str(product_id) and order_status == "Accept":
                        count = int(items.get('total_count'))
                        print("Order ID:", id_product, "Count:", count, "Order Status:", order_status)

                        # Reduce stock and save
                        product.product_stock = max(stock - count, 0)  # Prevent negative stock
                        product.save()
                        updated_products.append(product)

        # Serialize all updated products
        serializer = ProductListSerializer(updated_products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




class Total_counts_dashboard(APIView):

    permission_classes = [IsAuthenticated]
 
    def get(self,request):
        active_customer_count = Customer.objects.filter(status=False).count()
        print("Active customers:", active_customer_count)

        # order_count = sum(len(order.product_items) for order in Order_products.objects.all() if isinstance(order.product_items, list))
        # print("Total product count in all orders:", order_count)

        response_data = {
            "total_products" : Product_list.objects.count(),
            "total_category" : Product_Category.objects.count(),
            "active_customer_count":active_customer_count,
            "order_count":Order_products.objects.count()
            }
        return Response(response_data)


class Update_customer_status(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        # Extract status from request data
        status = request.data.get("status", None)

        # Ensure status is a boolean
        if not isinstance(status, bool):
            return Response({"error": "The request must contain a boolean 'status' field."}, status=400)

        # Get the customer object or return 404
        customer = get_object_or_404(Customer, id=id)

        # Convert boolean to a string to match CharField
        customer.status = status  
        customer.save()

        # Serialize and return updated customer data
        serializer = Register_custumerSerializer(customer)
        return Response(serializer.data, status=200)
        


# class Total_orders_list(APIView):
#     permission_classes = [AllowAny]
    
#     def get(self, request):

#         order_list = Order_products.objects.all()
        
#         if not order_list:
#             return Response({"error": "No orders found"}, status=404)

#         final_list = []
#         product_ids = set()

#         # Collect product IDs
#         for order in order_list:
#             product_items = order.product_items
#             products = product_items.get("products", [])
#             for data in products:
#                 product_ids.add(data["product_id"])

#         # Fetch product details in a dictionary
#         product_dict = {
#             str(product.id): {
#                 "product_name": product.product_name,
#                 "product_images": product.product_images if product.product_images else None,
#                 "product_category": product.product_category,
#                 "product_stock": product.product_stock,
#             }
#             for product in Product_list.objects.filter(id__in=product_ids)
#         }

#         # Process each order
#         for order in order_list:
#             userid = order.user_id
#             try:
#                 customer = Customer.objects.get(id=userid)
#             except customer.DoesNotExist:
#                 return Response({'error':'the custumer not exist'})
#             product_items = order.product_items  # Make sure to access the order's product_items

#             orderd_list = {
#                 "id": order.id,
#                 "userid": order.user_id,
#                 "username": customer.username,
#                 "address": product_items.get("address"),
#                 "order_id": product_items.get("order_id"),
#                 "order_track": product_items.get("order_track"),
#                 "date": product_items.get("date"),
#                 "final_amount": product_items.get("final_amount"),
#                 "profile_image": str(customer.profile_image.url) if customer.profile_image else None,
                
#             }

#             order_products = []
#             for product in product_items.get("products", []):
#                 product_id = str(product.get("product_id"))
#                 product_details = product_dict.get(product_id)

#                 if product_details:
#                     order_products.append(
#                         {
                            
#                             "product_id": product_id,
#                             "product_name": product_details["product_name"],
#                             "product_images": product_details["product_images"],
#                             "product_category": product_details["product_category"],
#                             "product_stock": product_details["product_stock"],
#                             "order_status": product.get("order_status"),
#                             "total_amount": product.get("total_amount"),
#                             "count": product.get("count"),
#                         }
#                     )

#             final_list.append(
#                 {
#                     "order_details": orderd_list,
#                     "order_products": order_products,
#                 }
#             ) 

#         return Response(final_list, status=200)


# class TotalOrdersList(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         order_list = Order_products.objects.all()

#         if not order_list:
#             return Response({"error": "No orders found"}, status=404)

#         final_list = []
#         product_ids = set()

#         # Collect product IDs from all orders
#         for order in order_list:
#             product_items = order.product_items
#             products = product_items.get("products", [])    
#             for data in products:
#                 product_ids.add(data["product_id"])

#         # Fetch product details in a dictionary for quick lookup
#         product_dict = {
#             str(product.id): {
#                 "product_name": product.product_name,
#                 "product_images": product.product_images if product.product_images else None,
#                 "product_category": product.product_category,
#                 "product_stock": product.product_stock,
#             }
#             for product in Product_list.objects.filter(id__in=product_ids)
#         }

#         # Process each order
#         for order in order_list:
#             userid = order.user_id
#             try:
#                 customer = Customer.objects.get(id=userid)
#             except Customer.DoesNotExist:
#                 return Response({'error': 'The customer does not exist'}, status=404)

#             product_items = order.product_items  # Get order details
            
#             # Prepare order details
#             orderd_list = {
#                 "id": order.id,
#                 "userid": order.user_id,
#                 "username": customer.username,
#                 "address": product_items.get("address"),
#                 "order_id": product_items.get("order_id"),
#                 "order_track": product_items.get("order_track"),
#                 "date": product_items.get("date"),
#                 "final_amount": product_items.get("final_amount"),
#                 "profile_image": str(customer.profile_image.url) if customer.profile_image else None,
#                 "order_products": []  # Order products will be inside order_details
#             }

#             # Fetch products in the order
#             for product in product_items.get("products", []):
#                 product_id = str(product.get("product_id"))
#                 product_details = product_dict.get(product_id)

#                 if product_details:
#                     orderd_list["order_products"].append({
#                         "product_id": product_id,
#                         "product_name": product_details["product_name"],
#                         "product_images": product_details["product_images"],
#                         "product_category": product_details["product_category"],
#                         "product_stock": product_details["product_stock"],
#                         "order_status": product.get("order_status"),
#                         "total_amount": product.get("total_amount"),
#                         "count": product.get("count"),
#                     })

#             # Append the order with embedded order_products
#             final_list.append({"order_details": orderd_list})

#         return Response(final_list, status=200)

class TotalOrdersList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        order_list = Order_products.objects.all()

        if not order_list:
            return Response({"error": "No orders found"}, status=404)

        final_list = []
        product_ids = set()

        # Collect product IDs from all orders
        for order in order_list:
            product_items = order.product_items
            products = product_items.get("products", [])
            for data in products:
                product_ids.add(data["product_id"])

        # Fetch product details in a dictionary for quick lookup
        product_dict = {
            str(product.id): {
                "product_name": product.product_name,
                "product_images": product.product_images if product.product_images else None,
                "product_category": product.product_category,
                "product_stock": product.product_stock,
            }
            for product in Product_list.objects.filter(id__in=product_ids)
        }

        # Process each order
        for order in order_list:
            userid = order.user_id

            try:
                customer = Customer.objects.get(id=userid)

                # Debugging: Print customer status
                print(f"Processing order for customer: {customer.username}, status: {customer.status}")

                # Check if the customer is active. If status is True, customer is inactive, so skip this order
                if customer.status == True:  # If status is True, the customer is inactive/blocked
                    print(f"Skipping order for inactive customer: {customer.username}")
                    continue

            except Customer.DoesNotExist:
                print(f"Deleting order for non-existing customer with user_id: {userid}")
                # Delete the order if the customer doesn't exist
                order.delete()
                continue

            product_items = order.product_items  # Get order details

            # Prepare order details
            orderd_list = {
                "id": order.id,
                "userid": order.user_id,
                "username": customer.username,
                "address": product_items.get("address"),
                "order_id": product_items.get("order_id"),
                "order_track": product_items.get("order_track"),
                "date": product_items.get("date"),
                "final_amount": product_items.get("final_amount"),
                "profile_image": str(customer.profile_image.url) if customer.profile_image else None,
                "order_products": []  # Order products will be inside order_details
            }

            # Fetch products in the order
            for product in product_items.get("products", []):
                product_id = str(product.get("product_id"))
                product_details = product_dict.get(product_id)

                if product_details:
                    orderd_list["order_products"].append({
                        "product_id": product_id,
                        "product_name": product_details["product_name"],
                        "product_images": product_details["product_images"],
                        "product_category": product_details["product_category"],
                        "product_stock": product_details["product_stock"],
                        "order_status": product.get("order_status"),
                        "total_amount": product.get("total_amount"),
                        "count": product.get("count"),
                    })

            # Append the order with embedded order_products
            final_list.append({"order_details": orderd_list})

        if not final_list:
            print("No valid orders to return for the active customers.")
            return Response({"message": "No valid orders found for active customers."}, status=200)

        return Response(final_list, status=200)  

class Search_all_products(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        search_term = request.data.get("search_term", "").strip()

        if not search_term:
            return Response({"error": "Search term is required"}, status=400)

        def search_products(search_term):
            query = Q()
            for field in Product_list._meta.get_fields():
                if hasattr(field, "attname"):  # Ensures it's a valid field
                    field_name = field.attname
                    field_type = field.get_internal_type()

                    # Apply filtering only to text-based fields
                    if field_type in ["CharField", "TextField"]:
                        query |= Q(**{f"{field_name}__icontains": search_term})  # Case-insensitive search

            return Product_list.objects.filter(query)

        products = search_products(search_term)

        if not products.exists():
            return Response({"message": "No matching products found"}, status=404)
        

        serializer = ProductListSerializer(products, many=True)
        return Response({"products": serializer.data}, status=200)

        # product_data = [{ 
        #     "id": p.id, "name": p.product_name, "category":p.product_category,"product_description":p.product_description,"product_stock":p.product_stock,"product_images":p.product_images if p.product_images else None,"prize_range":p.prize_range,"product_discount":p.product_discount,
        #     } for p in products]
        # return Response({"results": product_data}, status=200)


class SearchAllCustomer(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        search_term = request.data.get("search_term", "").strip()

        if not search_term:
            return Response({"error": "Search term is required"}, status=400)

        def search_customers(search_term):
            query = Q()
            for field in Customer._meta.get_fields():
                if hasattr(field, "attname"):  # Ensures it's a valid field
                    field_name = field.attname
                    field_type = field.get_internal_type()

                    if field_type in ["CharField", "TextField"]:
                        query |= Q(**{f"{field_name}__icontains": search_term})  # Case-insensitive search

            return Customer.objects.filter(query)

        customers = search_customers(search_term)

        if not customers.exists():
            return Response({"message": "No matching customers found"}, status=404)
        
        serializer = Register_custumerSerializer(customers, many=True)
        return Response({"products": serializer.data}, status=200)

        # product_data = [
        #     {
        #         "id": c.id,
        #         "name": c.username,
        #         "profile_image": request.build_absolute_uri(c.profile_image.url) if c.profile_image else None,
        #         "discount_individual": c.discount_individual,
        #         "permanent_adress":c.address,
        #         "phone_number":c.phone_number,
        #         "status":c.status
        #     }
        #     for c in customers
        # ]

        # return Response({"results": product_data}, status=200)




class SearchOrders(APIView):
    permission_classes = [IsAuthenticated]

    # def post(self, request):
    #     search_term = request.data.get("search_term", "").strip().lower()

    #     if not search_term:
    #         return Response({"error": "Search term is required"}, status=400)

    #     filtered_orders = []

    #     # **Step 1: Search in user_id with icontains**
    #     order_list = Order_products.objects.filter(
    #         Q(user_id__icontains=search_term)  # Partial match for user_id
    #     )

    #     # **Step 2: Search in product_items**
    #     if not order_list.exists(): 
    #         all_orders = Order_products.objects.all()

    #         for order in all_orders:
    #             try:
    #                 product_items = json.loads(order.product_items) if isinstance(order.product_items, str) else order.product_items
    #             except json.JSONDecodeError:
    #                 continue  # Skip if JSON is invalid

    #             matching_products = [
    #                 product for product in product_items
    #                 if search_term in str(product.get("order_track", "")).lower()
    #                 or search_term in str(product.get("order_id", "")).lower()
    #                 or search_term in str(product.get("date", "")).lower()
    #                 or search_term in str(product.get("username", "")).lower()
    #             ]

    #             if matching_products:
    #                 filtered_orders.append({
    #                     "product_items": matching_products
    #                 })
    #     else:
    #         # Directly add matching orders
    #         filtered_orders = [
    #             {"id": order.id, "user_id": order.user_id, "product_items": order.product_items}
    #             for order in order_list
    #         ]
    #     if not filtered_orders:
    #         return Response({"message": "No matching orders found"}, status=404)

    #     return Response({"orders": filtered_orders}, status=200)

    def post(self, request):
        search_term = request.data.get("search_term", "").strip().lower()

        if not search_term:
            return Response({"error": "Search term is required"}, status=400)

        filtered_orders = []

        # **Step 1: Search in user_id with icontains**
        order_list = Order_products.objects.filter(
            Q(user_id__icontains=search_term)  # Partial match for user_id
        )

        # **Step 2: Search in product_items**
        if not order_list.exists():
            all_orders = Order_products.objects.all()

            for order in all_orders:
                try:
                    product_items = json.loads(order.product_items) if isinstance(order.product_items, str) else order.product_items
                except json.JSONDecodeError:
                    continue  # Skip if JSON is invalid
                cutumer_id =int(order.user_id)
                cutumer_list = Customer.objects.get(id =cutumer_id)
                # for product_item in product_items:
                product_array = []  # To store enriched product details

                # Check if this order matches the search term
                if (
                    search_term in str(product_items.get("order_track", "")).lower()
                    or search_term in str(product_items.get("order_id", "")).lower()
                    or search_term in str(product_items.get("date", "")).lower()
                    or search_term in str(product_items.get("username", "")).lower()
                ):
                    # Get all product IDs from this order
                    product_ids = [product["product_id"] for product in product_items.get("products", [])]

                    # Fetch all product details at once (to avoid N+1 queries)
                    product_details_dict = {
                        str(prod.id): prod
                        for prod in Product_list.objects.filter(id__in=product_ids)
                    }

                    # Map products with additional details
                    for product in product_items.get("products", []):
                        product_id = str(product.get("product_id"))
                        product_details = product_details_dict.get(product_id)

                        if product_details:  # If product exists in the database
                            product_array.append(
                                {
                                    "product_id": product_id,
                                    "product_name": product_details.product_name,
                                    "product_images": product_details.product_images,
                                    "product_category": product_details.product_category,
                                    "product_stock": product_details.product_stock,
                                    "order_status": product.get("order_status"),
                                    "total_amount": product.get("total_amount"),
                                    "count": product.get("count")
                                }
                            )

                    # Store order details with enriched product data
                    order_data = {
                        "order_id": product_items.get("order_id"),
                        "username": cutumer_list.username,
                        "profile_image":str(cutumer_list.profile_image) if cutumer_list.profile_image else None,
                        "final_amount": product_items.get("final_amount"),
                        "address": product_items.get("address"),
                        "date": product_items.get("date"),
                        "order_track": product_items.get("order_track"),
                        "order_products": product_array,  # Store fully enriched product details
                        
                    }
                    filtered_orders.append(order_data)

        else:
            # Directly add matching orders
            for order in order_list:
                try:
                    product_items = json.loads(order.product_items) if isinstance(order.product_items, str) else order.product_items
                except json.JSONDecodeError:
                    continue  # Skip if JSON is invalid

                # for product_item in product_items:
                product_array = []

                # Get all product IDs from this order
                product_ids = [product.get("product_id") for product in product_items.get("products", [])]

                # Fetch all product details at once (to avoid N+1 queries)
                product_details_dict = {
                    str(prod.id): prod
                    for prod in Product_list.objects.filter(id__in=product_ids)
                }

                for product in product_items.get("products", []):
                    product_id = str(product.get("product_id"))
                    product_details = product_details_dict.get(product_id)

                    if product_details:
                        product_array.append(
                            {
                                "product_id": product_id,
                                "product_name": product_details.product_name,
                                "product_images": product_details.product_images,
                                "product_category": product_details.product_category,
                                "product_stock": product_details.product_stock,
                                "order_status": product.get("order_status"),
                                "total_amount": product.get("total_amount"),
                                "count": product.get("count")
                            }
                        )

                order_data = {
                    "order_id": product_items.get("order_id"),
                    "username": product_items.get("username"),
                    "final_amount": product_items.get("final_amount"),
                    "address": product_items.get("address"),
                    "date": product_items.get("date"),
                    "order_track": product_items.get("order_track"),
                    "products": product_array
                }
                filtered_orders.append(order_data)

        if not filtered_orders:
            return Response({"message": "No matching orders found"}, status=404)

        return Response({"orders": filtered_orders}, status=200)



    
# class Enquiry_send(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         serializer = EnquirySerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=201)  # Use 201 for resource creation
#         else:
#             return Response({"message": "Validation failed", "errors": serializer.errors}, status=400)  # Use 400 for bad request

        
#     def get(self, request):
#         try:
#             enquiry = Enquiry.objects.all()
#         except Error:
#             return Response({"error": "No enquiries found"}, status=status.HTTP_404_NOT_FOUND)
#         enquiry_list = []

#         for items in enquiry:
#             product_id = int(items.product_id)
#             print("The product ID is:", product_id)
#             try:
#                 product = Product_list.objects.get(id=product_id)
#             except Product_list.DoesNotExist:
#                 print(f"Product with ID {product_id} not found.")
#                 continue  # Skip this enquiry if the product does not exist
#             user = int(items.user_id)
#             try:
#                 customer = Customer.objects.get(id=user)
#             except Customer.DoesNotExist:
#                 print(f"Customer with ID {user} not found.")
#                 continue

#             print("The product list:", product)

#             enquiry_list.append({
#                 "user_id": user,
#                 "username":customer.username,
#                 "phone_number":customer.phone_number,
#                 "product_name": product.product_name,
#                 "product_image": product.product_images if product.product_images else None,  # Convert to URL string
#                 "product_description": product.product_description,
#                 "product_category": product.product_category,
#                 "prize_range": product.prize_range,
#                 "product_stock": product.product_stock,
#                 "message": items.message
#             })

#         if enquiry_list:
#             return Response(enquiry_list, status=status.HTTP_200_OK)
#         else:
#             return Response({"error": "No enquiries found"}, status=status.HTTP_404_NOT_FOUND)

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from twilio.twiml.messaging_response import MessagingResponse

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == 'POST':
        incoming_msg = request.POST.get('Body', '').strip()
        from_number = request.POST.get('From', '')
        
        # You can add logic to reply or process the incoming message
        response = MessagingResponse()
        
        if incoming_msg.lower() == 'hi':
            response.message("Hello! How can I help you?")
        else:
            response.message("Thanks for your message: " + incoming_msg)
        
        return HttpResponse(str(response), content_type='application/xml')
    else:
        return HttpResponse("Only POST allowed", status=405)


from twilio.rest import Client
from django.conf import settings

class Enquiry_send(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EnquirySerializer(data=request.data)
        if serializer.is_valid():
            enquiry = serializer.save()

            # WhatsApp Message Logic
            try:
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

                customer = Customer.objects.get(id=enquiry.user_id)
                product = Product_list.objects.get(id=enquiry.product_id)

                message_body = (
                    f" New enquiry received!\n\n"
                    f" Customer: {customer.username}\n"
                    f" Phone: {customer.phone_number}\n"
                    f" Product: {product.product_name}\n"
                    f" Message: {enquiry.message}"
                )

                # Send to business owner or admin WhatsApp (must be joined to sandbox)
                client.messages.create(
                    from_='whatsapp:+14155238886',  # Twilio Sandbox Number
                    body=message_body,
                    to='whatsapp:+918129106509'  # Must be pre-joined to the sandbox
                )

            except Exception as e:
                print(f" Error sending WhatsApp message: {str(e)}")

            return Response(serializer.data, status=201)
        else:
            return Response(
                {"message": "Validation failed", "errors": serializer.errors}, 
                status=400
            )
        


    def get(self, request):
        try:
            enquiry = Enquiry.objects.all()
        except Error:
            return Response({"error": "No enquiries found"}, status=status.HTTP_404_NOT_FOUND)
        enquiry_list = []

        for items in enquiry:
            product_id = int(items.product_id)
            print("The product ID is:", product_id)
            try:
                product = Product_list.objects.get(id=product_id)
            except Product_list.DoesNotExist:
                print(f"Product with ID {product_id} not found.")
                continue  # Skip this enquiry if the product does not exist
            user = int(items.user_id)
            try:
                customer = Customer.objects.get(id=user)
            except Customer.DoesNotExist:
                print(f"Customer with ID {user} not found.")
                continue

            print("The product list:", product)

            enquiry_list.append({
                "user_id": user,
                "username":customer.username,
                "phone_number":customer.phone_number,
                "product_name": product.product_name,
                "product_image": product.product_images if product.product_images else None,  # Convert to URL string
                "product_description": product.product_description,
                "product_category": product.product_category,
                "prize_range": product.prize_range,
                "product_stock": product.product_stock,
                "message": items.message
            })

        if enquiry_list:
            return Response(enquiry_list, status=status.HTTP_200_OK)
        else:
            return Response({"error": "No enquiries found"}, status=status.HTTP_404_NOT_FOUND)



class Top_products(APIView):

    permission_classes = []

    def get(self, request):
        see_more = request.query_params.get("see_more", "false").lower() == "true"
        orders_list = Order_products.objects.all()
        response_data = []
        seen_products = set()

        if orders_list.exists():
            print("Orders list count:", orders_list.count())

            for orders in orders_list:
                product_items = orders.product_items
                print("Product items:", product_items)

                # Parse JSON if product_items is a string
                if isinstance(product_items, str):
                    try:
                        product_items = json.loads(product_items)
                    except json.JSONDecodeError as e:
                        print("JSON Decode Error:", e, "| Product items:", product_items)
                        continue

                if not isinstance(product_items, dict):
                    continue

                for items in product_items.get('products', []):
                    print("items:", items)

                    if not isinstance(items, dict):
                        continue

                    if items.get('order_status') == 'accepted':
                        product_id = items.get('product_id')
                        print('The product id with status accepted:', product_id)

                        if product_id in seen_products:
                            continue

                        try:
                            product_obj = Product_list.objects.get(id=product_id)
                        except Product_list.DoesNotExist:
                            continue

                        seen_products.add(product_id)

                        response_data.append({
                            'product_id': product_id,
                            'product_name': product_obj.product_name,
                            'product_images': product_obj.product_images if product_obj.product_images else None,
                            'product_description': product_obj.product_description,
                            'product_discount': product_obj.product_discount if product_obj.product_discount else None,
                            'product_category': product_obj.product_category,
                            'prize_range': product_obj.prize_range,
                            'product_stock': product_obj.product_stock,
                            'order_status': items.get('order_status')
                        })

        # Apply 6-product limit only if see_more is False
        if not see_more:
            response_data = response_data[:6]
        if not response_data :
            try:
                all_products = list(Product_list.objects.all())
                print('the product is', all_products)
            except Product_list.DoesNotExist:
                return Response({'error': 'Product_list DoesNotExist.'}, status=400)

            if len(all_products) >= 1:
                products_list = random.sample(all_products, k=len(all_products))
                serializer = ProductListSerializer(products_list, many=True)
                return Response(serializer.data, status=200)
            else:
                return Response({'error': 'Not enough products to sample from.'}, status=400) 

        return Response(response_data, status=status.HTTP_200_OK)
        


class slider_Adds(APIView): 
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        image = request.FILES.get('image')
        if not image:
            return Response({'error': 'The image file is required'}, status=400)

        try:
            # Upload image to Cloudinary
            upload_result = cloudinary.uploader.upload(image, folder="slider_images/")

            # Store only the public_id in the model
            slider = Slider_Add.objects.create(slider_image=upload_result["public_id"])

            return Response({
                'message': 'Image uploaded successfully',
                'image_url': cloudinary.CloudinaryImage(slider.slider_image).build_url()
            }, status=201)

        except Exception as e:
            return Response({'error': f'Upload failed: {str(e)}'}, status=500)


        

    def get(self, request):
        sliders = Slider_Add.objects.all()

        if not sliders.exists():
            return Response({'error': 'No images found'}, status=404)

        # Use the serializer to return the correct image URL
        serializer = Slider_Add_Serializer(sliders, many=True)
        for sliders_data, sliders in zip(serializer.data, sliders):
            sliders_data["id"] = sliders.id  # Attach the `id` field
        return Response(serializer.data, status=200)

    # def patch(self, request, id):
    #     slider_item = get_object_or_404(Slider_Add, id=id)  # Returns 404 if not found
    #     new_image = request.FILES.get('new_image')

    #     if not new_image:
    #         return Response({'error': 'No new image provided'}, status=400)

    #     try:
    #         upload_result = cloudinary.uploader.upload(new_image)
    #         image_url = upload_result.get("secure_url")

    #         slider_item.slider_image = image_url
    #         slider_item.save()  # Save updated image URL

    #         # Serialize the updated object
    #         serializer = Slider_Add_Serializer(slider_item)
    #         return Response(serializer.data, status=200)
        
    #     except Exception as e:
    #         return Response({'error': str(e)}, status=500)
    
    def delete(self,request,id):
        slider_item = get_object_or_404(Slider_Add, id=id)
        if slider_item.slider_image:
            try:
                cloudinary.uploader.destroy(slider_item.slider_image.public_id)
            except Exception as e:
                return Response({"error": f"Failed to delete old image from Cloudinary: {str(e)}"}, status=500)
        if slider_item:
            slider_item.delete()
            return Response({"message":"the item deleted succefully"},status=200)
        
        return Response({'error': 'No item check id'}, status=400)
        


