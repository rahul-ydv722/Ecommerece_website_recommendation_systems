from django.contrib import admin

# Register your models here.
from .models import *
# Register your models here.
admin.site.register(Item)
admin.site.register(CartItem)
admin.site.register(Categories)
admin.site.register(Order)
admin.site.register(UserInteraction)
admin.site.register(Recommendation) 