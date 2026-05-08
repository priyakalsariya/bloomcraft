from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('occasion/', views.occasion, name='occasion'),
    path('select/<str:occ>',views.select_occasion,name='select_occasion'),
    path('builder/',views.builder,name='builder'),
    path('generate/',views.generate_bouquet,name='generate'),
    path('gallery/', views.gallery, name='gallery'),
    path('download/<int:bouquet_id>/', views.download_image, name='download_image'),
    path('delete/<int:bouquet_id>/', views.delete_bouquet, name='delete_bouquet'),
    path('cart/', views.cart, name='cart'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('remove-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('track/<int:order_id>/', views.track_order, name='track_order'),
    path('invoice/<int:order_id>/', views.download_invoice, name='download_invoice'),
]