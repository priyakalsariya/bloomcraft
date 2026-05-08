from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Flower, Leaf, Accessory, Paper,Bouquet,CartItem,Order,OrderItem
from django.http import HttpResponse
import requests
import os
import urllib.parse
from django.shortcuts import get_object_or_404
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse


# ✅ Load API key
HF_API_KEY = os.getenv("HF_API_KEY")


def home(request):
    return render(request, 'home.html')


@login_required
def occasion(request):
    return render(request, 'bouquet/occasion.html')


@login_required
def select_occasion(request, occ):
    request.session['occasion'] = occ
    return redirect('builder')


@login_required
def builder(request):
    flowers = Flower.objects.all()
    leaves = Leaf.objects.all()
    accessories = Accessory.objects.all()
    papers = Paper.objects.all()

    if request.method == "POST":
        request.session['flowers'] = request.POST.getlist('flowers')
        request.session['leaves'] = request.POST.getlist('leaves')
        request.session['accessories'] = request.POST.getlist('accessories')
        request.session['paper'] = request.POST.get('paper')

        return redirect('generate')

    return render(request, 'bouquet/builder.html', {
        'flowers': flowers,
        'leaves': leaves,
        'accessories': accessories,
        'papers': papers
    })


@login_required
def generate_bouquet(request):

    # ✅ Get session data
    flower_ids = list(map(int, request.session.get('flowers', [])))
    leaf_ids = list(map(int, request.session.get('leaves', [])))
    accessory_ids = list(map(int, request.session.get('accessories', [])))
    paper_id = request.session.get('paper')

    # ✅ Fetch objects
    flowers = Flower.objects.filter(id__in=flower_ids)
    leaves = Leaf.objects.filter(id__in=leaf_ids)
    accessories = Accessory.objects.filter(id__in=accessory_ids)
    paper = Paper.objects.filter(id=paper_id).first()

    occasion = request.session.get('occasion')

    # ✅ Build prompt
    prompt = f"Beautiful {occasion} flower bouquet, "

    if flowers:
        prompt += ", ".join([f.name for f in flowers]) + ", "

    if leaves:
        prompt += "green " + ", ".join([l.name for l in leaves]) + ", "

    if accessories:
        prompt += "decorated with " + ", ".join([a.name for a in accessories]) + ", "

    if paper:
        prompt += f"wrapped in {paper.name} paper, "

    prompt += "high quality, realistic, soft lighting, professional photography"

    # Pollinations API 
    encoded_prompt = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"

     #  CALCULATE PRICE
    total_price = 0

    total_price += sum(f.price for f in flowers)
    total_price += sum(l.price for l in leaves)
    total_price += sum(a.price for a in accessories)

    if paper:
        total_price += paper.price

    total_price += 50   # base making charge

    if total_price > 300:
        total_price *= 0.9   # 10% discount

    delivery_charge = 40
    total_price += delivery_charge

    total_price = int(total_price)

    #to save image 
    bouquet = Bouquet.objects.create(
    user=request.user,
    prompt=prompt,
    image_url=image_url,
    price=total_price
)

    return render(request, 'bouquet/generate.html', {
        'prompt': prompt,
        'image_url': image_url,
        'price':total_price,
        'bouquet_id': bouquet.id,
    })

#save in gallary
@login_required
def gallery(request):
    bouquets=Bouquet.objects.filter(user=request.user).order_by('-created_at')

    return render(request,'bouquet/gallery.html',{'bouquets':bouquets})

#download image
@login_required
def download_image(request,bouquet_id):
    bouquet=Bouquet.objects.get(id=bouquet_id,user=request.user)

    response=requests.get(bouquet.image_url)

    if response.status_code==200:
        image_response=HttpResponse(response.content,content_type="image/jpeg")
        image_response['Content-Disposition']='attachment; filename="bouquet.jpg"'

        return image_response
    return HttpResponse("Failed to download image")

@login_required
def delete_bouquet(request, bouquet_id):
    bouquet = get_object_or_404(Bouquet, id=bouquet_id, user=request.user)

    bouquet.delete()

    return redirect('gallery')

@login_required
def add_to_cart(request):
    if request.method == "POST":
        bouquet_id = request.POST.get("bouquet_id")
        bouquet = Bouquet.objects.get(id=bouquet_id)

        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            bouquet=bouquet
        )

        if not created:
            cart_item.quantity += 1
            cart_item.save()

    return redirect('cart')

@login_required
def cart(request):
    items = CartItem.objects.filter(user=request.user)

    total = sum(item.bouquet.price * item.quantity for item in items)

    return render(request, 'bouquet/cart.html', {
        'items': items,
        'total': total
    })

@login_required
def remove_from_cart(request, item_id):
    item = CartItem.objects.get(id=item_id, user=request.user)
    item.delete()
    return redirect('cart')

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)

    if request.method == "POST":
        address = request.POST.get("address")
        phone = request.POST.get("phone")
        payment_method = request.POST.get("payment_method")

        total = sum(item.bouquet.price * item.quantity for item in cart_items)

        order = Order.objects.create(
            user=request.user,
            total_price=total,
            address=address,
            phone=phone,
            payment_method=payment_method,
            payment_status="Pending"
        )

        # Save items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                bouquet=item.bouquet,
                quantity=item.quantity
            )

        # Clear cart
        cart_items.delete()

        return redirect('order_success', order.id)

    return render(request, 'bouquet/checkout.html')

@login_required
def order_success(request, order_id):
    order = Order.objects.get(id=order_id)
    return render(request, 'bouquet/success.html', {'order': order})

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'bouquet/my_orders.html', {
        'orders': orders
    })

@login_required
def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    steps = ['Pending', 'Confirmed', 'Shipped', 'Out for Delivery', 'Delivered']

    current_index = steps.index(order.status)

    step_data = []
    for i, step in enumerate(steps):
        step_data.append({
            "name": step,
            "completed": i < current_index,
            "current": i == current_index
        })

    return render(request, 'bouquet/track_order.html', {
        'order': order,
        'step_data': step_data
    })

# @login_required
# def download_invoice(request, order_id):
#     order = get_object_or_404(Order, id=order_id, user=request.user)

#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'

#     doc = SimpleDocTemplate(response)
#     styles = getSampleStyleSheet()

#     elements = []

#     elements.append(Paragraph(f"Invoice - Order #{order.id}", styles['Title']))
#     elements.append(Spacer(1, 10))

#     elements.append(Paragraph(f"Customer: {request.user.username}", styles['Normal']))
#     elements.append(Paragraph(f"Address: {order.address}", styles['Normal']))
#     elements.append(Paragraph(f"Phone: {order.phone}", styles['Normal']))
#     elements.append(Paragraph(f"Payment Method: {order.payment_method}", styles['Normal']))
#     elements.append(Paragraph(f"Payment Status: {order.payment_status}", styles['Normal']))

#     elements.append(Spacer(1, 10))

#     for item in order.orderitem_set.all():
#         elements.append(Paragraph(
#             f"{item.bouquet.prompt} x {item.quantity} = ₹{item.bouquet.price}",
#             styles['Normal']
#         ))

#     elements.append(Spacer(1, 10))
#     elements.append(Paragraph(f"Total: ₹{order.total_price}", styles['Title']))

#     doc.build(elements)

#     return response
@login_required
def download_invoice(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)

    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.txt"'

    response.write(f"INVOICE - Order #{order.id}\n")
    response.write(f"Customer: {request.user.username}\n")
    response.write(f"Address: {order.address}\n")
    response.write(f"Phone: {order.phone}\n")
    response.write(f"Payment Method: {order.payment_method}\n")
    response.write(f"Status: {order.status}\n")
    response.write("\nItems:\n")

    total = 0
    for item in items:
        line = item.quantity * item.bouquet.price
        total += line
        response.write(f"{item.bouquet.prompt} x {item.quantity} = ₹{line}\n")

    response.write(f"\nTotal Amount: ₹{total}\n")

    return response



