# ventas/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db import transaction
import io
from reportlab.pdfgen import canvas
from .models import Producto, Venta, DetalleVenta
from .forms import ProductoForm
from clientes.models import Cliente

# Página de inicio
def index(request):
    return render(request, 'ventas/index.html')


# Listar productos
def productos_list(request):
    productos = Producto.objects.all()
    return render(request, 'ventas/productos_list.html', {'productos': productos})


# Agregar producto (usa ProductoForm definido en forms.py)
def producto_add(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('productos_list')
    else:
        form = ProductoForm()
    return render(request, 'ventas/producto_form.html', {'form': form})


# Editar producto
def producto_edit(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('productos_list')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'ventas/producto_form.html', {'form': form, 'producto': producto})


# Eliminar producto
def producto_delete(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
        return redirect('productos_list')
    return render(request, 'ventas/producto_delete.html', {'producto': producto})


# Registrar venta
def venta_add(request):
    productos = Producto.objects.all()
    clientes = Cliente.objects.all()

    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        cliente_obj = Cliente.objects.get(id=cliente_id) if cliente_id else None
        vendedor = request.user if request.user.is_authenticated else None

        # Crear venta y detalles dentro de una transacción
        with transaction.atomic():
            venta = Venta.objects.create(cliente=cliente_obj, vendedor=vendedor, total=0)

            for key, value in request.POST.items():
                if key.startswith('cantidad_'):
                    try:
                        producto_id = int(key.split('_', 1)[1])
                        cantidad = int(value)
                    except (IndexError, ValueError):
                        continue
                    if cantidad > 0:
                        producto = get_object_or_404(Producto, id=producto_id)
                        detalle = DetalleVenta(venta=venta, producto=producto, cantidad=cantidad)
                        detalle.save()  # el save() del modelo calcula subtotal y descuenta stock

            # Recalcular total y guardar
            total = sum(d.subtotal for d in venta.detalles.all())
            venta.total = total
            venta.save()

        return redirect('venta_detail', venta_id=venta.id)

    return render(request, 'ventas/venta_add.html', {
        'productos': productos,
        'clientes': clientes
    })


# Listar todas las ventas
def ventas_list(request):
    ventas = Venta.objects.all().order_by('-fecha')
    return render(request, 'ventas/ventas_list.html', {'ventas': ventas})


# Detalle de una venta
def venta_detail(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    detalles = venta.detalles.select_related('producto').all()
    total = sum(d.subtotal for d in detalles)
    return render(request, 'ventas/venta_detail.html', {
        'venta': venta,
        'detalles': detalles,
        'total': total
    })


# Generar PDF de UNA venta (factura)
def factura_pdf(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    detalles = venta.detalles.select_related('producto').all()

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    # Encabezado
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, "FACTURA DE VENTA")

    p.setFont("Helvetica", 12)
    cliente_txt = venta.cliente.nombre if venta.cliente else "Sin cliente"
    ruc_txt = venta.cliente.ruc if (venta.cliente and getattr(venta.cliente, 'ruc', None)) else "---"
    p.drawString(50, 770, f"Cliente: {cliente_txt}")
    p.drawString(50, 750, f"RUC: {ruc_txt}")
    vendedor_txt = venta.vendedor.username if venta.vendedor else "N/A"
    p.drawString(50, 730, f"Vendedor: {vendedor_txt}")
    p.drawString(50, 710, f"Fecha: {venta.fecha.strftime('%d/%m/%Y %H:%M')}")

    # Tabla
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 690, "Producto")
    p.drawString(300, 690, "Cantidad")
    p.drawString(400, 690, "Subtotal")

    y = 670
    total = 0
    for d in detalles:
        p.setFont("Helvetica", 12)
        p.drawString(50, y, d.producto.nombre)
        p.drawString(300, y, str(d.cantidad))
        p.drawString(400, y, f"{d.subtotal}")
        total += d.subtotal
        y -= 18
        if y < 60:
            p.showPage()
            y = 800

    p.setFont("Helvetica-Bold", 12)
    p.drawString(300, y - 10, f"TOTAL: {total}")

    p.showPage()
    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_venta_{venta.id}.pdf"'
    return response


# Generar PDF resumen de todas las ventas
def ventas_pdf(request):
    ventas = Venta.objects.all().order_by('-fecha')

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(180, 800, "REPORTE DE VENTAS")
    
    from datetime import datetime
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    p.setFont("Helvetica-Bold", 12)  # <-- negrita
    p.drawString(50, 780, f"Generado el: {fecha_actual}")     

    p.setFont("Helvetica", 11)
    y = 760
    for venta in ventas:
        cliente_txt = venta.cliente.nombre if venta.cliente else "Sin cliente"
        p.drawString(50, y, f"Venta {venta.id} | Cliente: {cliente_txt} | Total: {venta.total} | Fecha: {venta.fecha.strftime('%d/%m/%Y')}")
        y -= 16
        detalles = venta.detalles.select_related('producto').all()
        for d in detalles:
            p.drawString(70, y, f"- {d.producto.nombre} x{d.cantidad} = {d.subtotal}")
            y -= 12
            if y < 60:
                p.showPage()
                y = 800
        y -= 8
        if y < 60:
            p.showPage()
            y = 800

    p.showPage()
    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_ventas.pdf"'
    return response
