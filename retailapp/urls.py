from django.urls import path
from .views import *


urlpatterns = [
    path('', Home.as_view(),name='home'),
    path('api/product-category/', ProductCategoryView.as_view(), name='product-category'),
    path('api/Product_categoryUpdate/<int:id>/', Product_categoryUpdate.as_view(), name='Product_categoryUpdate'),
    path('api/ProductListPost/', ProductListPost.as_view(), name='ProductListPost'),
    path('api/ProduclistView/', ProduclistView.as_view(), name='ProduclistView'),
    path('api/ProduclistViewlimit/', ProduclistViewlimit.as_view(), name='ProduclistViewlimit'),
    path('api/Register/', Register_custumer.as_view(), name='Register'),
    path('api/Register_admin/', Register_admin.as_view(), name='Register_admin'),
    path('api/Login/', UserLoginView.as_view(), name='Login'),
    path('api/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('api/Search_history/', Search_history.as_view(), name='Search_history'),
    path('api/Newly_arrived/', Newly_arrived.as_view(), name='Newly_arrived'),
    path('api/Profile_update_custumer/<int:id>/', Profile_update_custumer.as_view(), name='Profile_update_custumer'),
    path('api/UpdateRegister/<int:id>/', UpdateRegister.as_view(), name='UpdateRegister'),
    path('api/Category_filter/', Category_filter.as_view(), name='Category_filter'),
    path('api/Product_updateanddelete/<int:id>/', Product_updateanddelete.as_view(), name='Product_updateanddelete'),
    path('api/ProductAddExtraImage/<int:id>/', ProductAddExtraImage.as_view(), name='ProductAddExtraImage'),
    path('api/Adding_cart/', Adding_cart.as_view(), name='Adding_cart'),
    path('api/Count_order_update/', Count_order_update.as_view(), name='Count_order_update'),
    path('api/Delete_all_cart/', Delete_all_cart.as_view(), name='Delete_all_cart'),
    path('api/order_products/', order_products.as_view(), name='order_products'),
    path('api/Update_order_status/', UpdateOrderStatus.as_view(), name='Update_order_status'),
    path('api/Update_tracking/<int:id>/', Update_tracking.as_view(), name='Update_tracking'),
    path('api/Stock_auto_update/', Stock_auto_update.as_view(), name='Stock_auto_update'),
    path('api/Total_counts_dashboard/', Total_counts_dashboard.as_view(), name='Total_counts_dashboard'),
    path('api/Update_customer_status/<int:id>/', Update_customer_status.as_view(), name='Update_customer_status'),
    path('api/Total_orders_list/', TotalOrdersList.as_view(), name='Total_orders_list'),
    path('api/Search_all_products/', Search_all_products.as_view(), name='Search_all_products'),
    path('api/SearchAllCustomer/', SearchAllCustomer.as_view(), name='SearchAllCustomer'),
    path('api/SearchOrders/', SearchOrders.as_view(), name='SearchOrders'),
    path('api/CancelOrder/', CancelOrder.as_view(), name='CancelOrder'),
    path('api/Enquiry_send/', Enquiry_send.as_view(), name='Enquiry_send'),
    path('api/Top_products/', Top_products.as_view(), name='Top_products'),
    path('api/slider_Adds/', slider_Adds.as_view(), name='slider_Adds'),
    path('api/slider_Adds/<int:id>/', slider_Adds.as_view(), name='slider_Adds-update'),

]



