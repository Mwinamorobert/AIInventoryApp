from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils.timezone import now, timedelta
import json
import pandas as pd
import numpy as np
import csv
import plotly.express as px
from prophet import Prophet
import plotly.graph_objects as go
from .models import InventoryItem, Supplier, Location


# -----------------------
# Utility - Anomaly Detection
# -----------------------
def detect_anomalies(items):
    if not items:
        return []

    quantities = np.array([item.quantity for item in items])
    mean = np.mean(quantities)
    std = np.std(quantities)

    print("Quantities:", quantities)
    print("Mean:", mean, "Std:", std)

    if std == 0:
        return []

    flagged = [item for item in items if abs((item.quantity - mean) / std) > 2]
    print("Flagged:", [f"{item.name} → {item.quantity}" for item in flagged])
    return flagged



# -----------------------
# Dashboard View & Data API
# -----------------------
@login_required
def dashboard_view(request):
    suppliers = Supplier.objects.filter(user=request.user)
    locations = Location.objects.filter(user=request.user)
    location_filter = request.GET.get('location', '')
    # Placeholder for forecast_fig, anomalies_fig, and stock_fig to avoid undefined variable errors
    forecast_fig = px.line(x=[0], y=[0], title="Forecast Chart (Placeholder)")
    anomalies_fig = px.bar(x=['None'], y=[0], title="Anomalies Detected (Placeholder)")
    stock_fig = px.bar(x=['None'], y=[0], title="Stock Trends (Placeholder)")

    return render(request, 'dashboard.html', {
        'suppliers': suppliers,
        'locations': locations,
        'location_filter': location_filter,
        'forecast_chart_data': forecast_fig.to_json(),
        'anomalies_chart_data': anomalies_fig.to_json(),
        'stock_trend_data': stock_fig.to_json()
    })


@login_required
def get_dashboard_data_api(request):
    location_filter = request.GET.get('location', '')
    items = InventoryItem.objects.filter(user=request.user)
    if location_filter:
        items = items.filter(location__name=location_filter)

    total_items = items.count()
    total_value = items.aggregate(Sum('price'))['price__sum'] or 0

    # Stock trends
    stock_data = items.values('name').annotate(total=Sum('quantity')).order_by('name')
    stock_chart = px.line(pd.DataFrame(stock_data), x='name', y='total', title='Stock Levels Over Time', markers=True)

    # Grouped location/supplier
    location_data = items.values('location__name').annotate(total=Sum('quantity'))
    supplier_data = items.values('supplier__name').annotate(total=Sum('quantity'))
    location_chart = px.pie(location_data, names='location__name', values='total', title='Stock by Location')
    supplier_chart = px.bar(supplier_data, x='supplier__name', y='total', title='Supplier Performance')

    # Forecast: simulate demand over days per item
    forecast_df = pd.DataFrame(list(items.values('created_at', 'quantity', 'name')))
    forecast_fig = go.Figure()
    if not forecast_df.empty:
        forecast_df['created_at'] = pd.to_datetime(forecast_df['created_at']).dt.date
        grouped = forecast_df.groupby(['created_at', 'name'])['quantity'].sum().reset_index()
        for name in grouped['name'].unique():
            item_data = grouped[grouped['name'] == name]
            forecast_fig.add_trace(go.Scatter(x=item_data['created_at'], y=item_data['quantity'],
                                              mode='lines+markers', name=name))
        forecast_fig.update_layout(title='Demand Forecast')

    # Anomalies: basic detection (quantity > 100)
    items = InventoryItem.objects.filter(user=request.user)  # Ensure items is defined
    items = InventoryItem.objects.filter(user=request.user)  # Ensure items is defined
    anomalies = [item for item in items if item.quantity > 100]
    anomalies_df = pd.DataFrame([{'name': item.name, 'quantity': item.quantity} for item in anomalies])
    anomalies_fig = px.bar(anomalies_df, x='name', y='quantity', title='Anomalies Detected') \
        if not anomalies_df.empty else px.bar(x=['None'], y=[0], title='No Anomalies Detected')

    item_list = [{
        'id': item.id,
        'name': item.name,
        'quantity': item.quantity,
        'price': float(item.price),
        'supplier': item.supplier.name if item.supplier else 'N/A',
        'location': item.location.name if item.location else 'N/A'
    } for item in items]

    return JsonResponse({
        'total_items': total_items,
        'total_value': total_value,
        'stock_chart_data': stock_chart.to_json(),
        'location_chart_data': location_chart.to_json(),
        'supplier_chart_data': supplier_chart.to_json(),
        'forecast_chart_data': forecast_fig.to_json(),
        'anomalies_chart_data': anomalies_fig.to_json(),
        'items': item_list
    })




# -----------------------
# Inventory Item API
# -----------------------
@login_required
def add_item_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        location, _ = Location.objects.get_or_create(name=data['location'], defaults={'user': request.user})
        supplier, _ = Supplier.objects.get_or_create(name=data['supplier'], defaults={'user': request.user})
        InventoryItem.objects.create(
            user=request.user,
            name=data['name'],
            quantity=data['quantity'],
            price=data['price'],
            supplier=supplier,
            location=location
        )
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def delete_item_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item = InventoryItem.objects.get(id=data['id'], user=request.user)
        item.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def get_item_api(request, id):
    item = InventoryItem.objects.get(id=id, user=request.user)
    return JsonResponse({
        'name': item.name,
        'quantity': item.quantity,
        'price': float(item.price),
        'supplier': item.supplier.name if item.supplier else '',
        'location': item.location.name if item.location else ''
    })


@login_required
def edit_item_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item = InventoryItem.objects.get(id=data['id'], user=request.user)
        location, _ = Location.objects.get_or_create(name=data['location'], defaults={'user': request.user})
        supplier, _ = Supplier.objects.get_or_create(name=data['supplier'], defaults={'user': request.user})
        item.name = data['name']
        item.quantity = data['quantity']
        item.price = data['price']
        item.location = location
        item.supplier = supplier
        item.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


# -----------------------
# Location Views
# -----------------------
@login_required
def locations_view(request):
    locations = Location.objects.filter(user=request.user).annotate(
        item_count=Count('inventoryitem'),
        total_stock=Sum('inventoryitem__quantity')
    )
    for location in locations:
        items = InventoryItem.objects.filter(location=location)
        location.items_list = [{'name': item.name, 'quantity': item.quantity} for item in items]
    return render(request, 'locations.html', {'locations': locations})


@login_required
def add_location_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name')
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Location name is required'}, status=400)
        location, created = Location.objects.get_or_create(name=name, defaults={'user': request.user})
        if not created:
            return JsonResponse({'status': 'error', 'message': 'Location already exists'}, status=400)
        return JsonResponse({'status': 'success', 'location': {'id': location.id, 'name': location.name}})


@login_required
def edit_location(request, location_id):
    location = Location.objects.get(id=location_id, user=request.user)
    if request.method == 'POST':
        data = json.loads(request.body)
        location.name = data['name']
        location.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def delete_location(request, location_id):
    location = Location.objects.get(id=location_id, user=request.user)
    if request.method == 'POST':
        location.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


# -----------------------
# Supplier Views
# -----------------------
@login_required
def suppliers_view(request):
    suppliers = Supplier.objects.filter(user=request.user).annotate(
        item_count=Count('inventoryitem'),
        total_stock=Sum('inventoryitem__quantity')
    )
    return render(request, 'suppliers.html', {'suppliers': suppliers})


@login_required
def add_supplier_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name')
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Supplier name is required'}, status=400)
        supplier, created = Supplier.objects.get_or_create(name=name, defaults={'user': request.user})
        if not created:
            return JsonResponse({'status': 'error', 'message': 'Supplier already exists'}, status=400)
        return JsonResponse({'status': 'success', 'supplier': {'id': supplier.id, 'name': supplier.name}})


@login_required
def edit_supplier(request, supplier_id):
    supplier = Supplier.objects.get(id=supplier_id, user=request.user)
    if request.method == 'POST':
        data = json.loads(request.body)
        supplier.name = data['name']
        supplier.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def delete_supplier(request, supplier_id):
    supplier = Supplier.objects.get(id=supplier_id, user=request.user)
    if request.method == 'POST':
        supplier.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


# -----------------------
# Insights Page
# -----------------------
@login_required
def insights_view(request):
    items = InventoryItem.objects.filter(user=request.user)

    df = pd.DataFrame(list(items.values('name', 'quantity', 'created_at')))
    if not df.empty:
        # Normalize time: remove timezone to avoid Prophet issues and ensure plot works
        df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)
        df = df.sort_values(by='created_at')

        # Group data per item per date
        df['created_at'] = df['created_at'].dt.floor('min')  # collapse to minute if needed
        grouped = df.groupby(['created_at', 'name'])['quantity'].sum().reset_index()

        # Plot as proper time-series lines
        forecast_fig = px.line(
            grouped,
            x='created_at',
            y='quantity',
            color='name',
            title='Demand Forecast',
            markers=True,
            line_shape='linear'
        )
        forecast_fig.update_layout(
            xaxis_title='Date & Time',
            yaxis_title='Quantity'
        )
    else:
        forecast_fig = px.line(x=[], y=[], title='Demand Forecast (No Data)', markers=True)
        forecast_fig.update_layout(xaxis_title='Date & Time', yaxis_title='Quantity')

    # ----- Anomalies Chart -----
    anomalies = [item for item in items if item.quantity > 100]
    anomalies_df = pd.DataFrame([{'name': item.name, 'quantity': item.quantity} for item in anomalies])
    if not anomalies_df.empty:
        anomalies_fig = px.bar(anomalies_df, x='name', y='quantity', title='Anomalies Detected')
    else:
        anomalies_fig = px.bar(x=[], y=[], title='No Anomalies Detected')

    # ----- Stock Trend -----
    stock_data = items.values('name').annotate(total=Sum('quantity')).order_by('-total')
    stock_fig = px.line(stock_data, x='name', y='total', title='Stock Trends', markers=True)

    # ----- Insights -----
    low_stock = [item for item in items if item.quantity < 10]
    low_stock_list = [{'name': item.name, 'quantity': item.quantity, 'location': item.location.name if item.location else 'N/A'} for item in low_stock]
    restock_suggestions = [{'name': item.name, 'suggested_quantity': max(100 - item.quantity, 0)} for item in items if item.quantity < 50]

    return render(request, 'insights.html', {
        'forecast_chart_data': forecast_fig.to_json(),
        'anomalies_chart_data': anomalies_fig.to_json(),
        'stock_trend_data': stock_fig.to_json(),
        'low_stock': low_stock_list,
        'restock_suggestions': restock_suggestions
    })
# -----------------------
# Export CSV
# -----------------------
@login_required
def export_inventory(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Quantity', 'Price', 'Supplier', 'Location'])
    for item in InventoryItem.objects.filter(user=request.user):
        writer.writerow([
            item.name,
            item.quantity,
            item.price,
            item.supplier.name if item.supplier else '',
            item.location.name if item.location else ''
        ])
    return response


# -----------------------
# Registration View
# -----------------------
def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'register.html')

        User.objects.create_user(username=username, password=password1)
        messages.success(request, "Account created successfully! You can now log in.")
        return redirect('login')

    return render(request, 'register.html')
