from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils.timezone import now
from collections import defaultdict
from .models import *
import random
from collections import defaultdict

def index(request):
    verification_msg = None  
    cart_count = 0

    if request.user.is_authenticated:
        user = request.user
        if user.email.endswith("@pg.sharda.ac.in"):
            verification_msg = "Verified by sharda"
        # Calculate cart count
        cart_count = CartItem.objects.filter(user=user, status='in_cart').count()
    
    categories = Categories.objects.all()
    selected_category = request.GET.get('category')
    query = request.GET.get('q')
    sort_option = request.GET.get('sort')

    items = Item.objects.all()

    if selected_category:
        items = items.filter(category__name=selected_category)

    if query:
        items = items.filter(Q(name__icontains=query))

    if sort_option == 'low_to_high':
        items = items.order_by('price')
    elif sort_option == 'high_to_low':
        items = items.order_by('-price')

    recommendations = []
    if request.user.is_authenticated:
        generate_recommendations(request.user)
        recommendations = Recommendation.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('item').order_by('-score')[:6]

    context = {
        'items': items,
        'categories': categories,
        'selected_category': selected_category,
        'query': query,
        'verification_msg': verification_msg,
        'recommendations': recommendations,
        'cart_count': cart_count,  # Add this line
    }
    return render(request, "index.html", context)

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt  # Temporarily disable CSRF for testing (remove in production)
@require_POST
@login_required
def AddToCartView(request, id):
    try:
        item = get_object_or_404(Item, id=id, is_active=True)
        user = request.user
        
        # Record the interaction
        UserInteraction.objects.create(
            user=user, 
            item=item, 
            interaction_type='add_to_cart'
        )

        # Add to cart or increment quantity
        cart_item, created = CartItem.objects.get_or_create(
            user=user,
            item=item,
            status='in_cart',
            defaults={'quantity': 1}
        )

        if not created:
            cart_item.quantity += 1
            cart_item.save()

        cart_count = CartItem.objects.filter(user=user, status='in_cart').count()
        
        return JsonResponse({
            'status': 'success',
            'message': f'{item.name} added to cart successfully',
            'cart_count': cart_count
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def CartView(request):
    # Get all cart items for the current user
    cart_items = CartItem.objects.filter(
        user=request.user,
        status='in_cart'
    ).select_related('item')
    
    # Calculate total bill without any stock checks
    total_bill = sum(item.item.price * item.quantity for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_bill': total_bill,
    }
    return render(request, 'cart.html', context)

@login_required
def RemoveFromCartView(request, item_id):
    try:
        cart_item = get_object_or_404(
            CartItem, 
            id=item_id, 
            user=request.user
        )
        cart_item.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Item removed from cart',
            'cart_count': CartItem.objects.filter(
                user=request.user, 
                status='in_cart'
            ).count()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, 'Logged in successfully!')
            return redirect('index')
        messages.error(request, 'Invalid username or password', extra_tags='login')
    
    return render(request, 'login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match!', extra_tags='register')
            return render(request, 'login.html', {'active_tab': 'signup'})
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken', extra_tags='register')
            return render(request, 'login.html', {'active_tab': 'signup'})
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered', extra_tags='register')
            return render(request, 'login.html', {'active_tab': 'signup'})
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email
            )
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('index')
    
    return render(request, 'login.html', {'active_tab': 'signup'})

@login_required
def logout_view(request):
    logout(request)
    return redirect('index')

from decimal import Decimal

@login_required
def process_order(request):
    if request.method == 'POST':
        try:
            cart_items = CartItem.objects.filter(
                user=request.user,
                status='in_cart'
            ).select_related('item')
            
            if not cart_items.exists():
                messages.error(request, 'Your cart is empty')
                return redirect('cart')

            # Create order
            order = Order.objects.create(
                user=request.user,
                total_price=sum(Decimal(str(ci.item.price)) * ci.quantity for ci in cart_items),
                shipping_address=request.POST.get('location', ''),
                phone=request.POST.get('mobile', ''),
                payment_reference=f"ORD-{now().timestamp()}"
            )
            order.items.set(cart_items)

            # Record purchases
            for cart_item in cart_items:
                UserInteraction.objects.create(
                    user=request.user,
                    item=cart_item.item,
                    interaction_type='purchase'
                )
            
            # Update cart items status to 'ordered' (instead of deleting)
            cart_items.update(status='ordered')
            messages.success(request, 'Order placed successfully!')
            return redirect('order_view')  
        except Exception as e:
            print(e)
            messages.error(request, f'Error processing order: {str(e)}')
            return redirect('cart')

    # GET request - show checkout page
    cart_items = CartItem.objects.filter(
        user=request.user,
        status='in_cart'
    ).select_related('item')
    
    if not cart_items.exists():
        return redirect('cart')

    total_price = sum(Decimal(str(item.item.price)) * item.quantity for item in cart_items)
    
    # Apply Sharda discount (using Decimal for the calculation)
    discount = Decimal('0')
    if request.user.email.endswith("@ug.sharda.ac.in"):
        discount = total_price * Decimal('0.10')
        total_price -= discount

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'discount': discount,
    }
    return render(request, 'checkout.html', context)


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )
    return render(request, 'order_detail.html', {'order': order})

@login_required
def order_view(request):
    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related(
        'items__item'
    ).order_by('-created_at')
    
    return render(request, 'order.html', {'orders': orders})

from django.db.models import Count, Sum
import random
from collections import defaultdict

def generate_recommendations(user):
    # Get all active items with their interaction counts
    items = Item.objects.filter(is_active=True).annotate(
        view_count=Count('interactions', filter=Q(interactions__interaction_type='view')),
        purchase_count=Count('interactions', filter=Q(interactions__interaction_type='purchase')),
        cart_count=Count('interactions', filter=Q(interactions__interaction_type='add_to_cart'))
    )
    
    # Calculate weighted scores for each item
    recommendations = []
    for item in items:
        
        score = (
            item.view_count * 1 + 
            item.cart_count * 3 + 
            item.purchase_count * 5
        )
        score *= (0.9 + random.random() * 0.1)
        recommendations.append((item, score))
    recommendations.sort(key=lambda x: x[1], reverse=True)
    user_interacted_items = UserInteraction.objects.filter(
        user=user
    ).values_list('item_id', flat=True)
    filtered_recommendations = [
        (item, score) for item, score in recommendations
        if item.id not in user_interacted_items
    ]
    if not filtered_recommendations:
        filtered_recommendations = recommendations[:10]
    Recommendation.objects.filter(user=user).delete()
    for item, score in filtered_recommendations[:6]:
        Recommendation.objects.create(
            user=user,
            item=item,
            score=score,
            algorithm_version='v4.0'
        )


# In your context_processors.py
def cart_count(request):
    count = 0
    if request.user.is_authenticated:
        count = CartItem.objects.filter(user=request.user, status='in_cart').count()
    return {'cart_count': count}

def item_detail(request, id):
    item = get_object_or_404(Item, id=id, is_active=True)
    
    if request.user.is_authenticated:
        UserInteraction.objects.create(
            user=request.user,
            item=item,
            interaction_type='view'
        )

    # Get related items
    related_items = Item.objects.filter(
        category=item.category,
        is_active=True
    ).exclude(id=id)[:4]

    context = {
        'item': item,
        'related_items': related_items
    }
    return render(request, 'item_detail.html', context)