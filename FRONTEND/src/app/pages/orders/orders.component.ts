import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

interface Order {
  codigoPedido: number;
  articulo: string;
  pvp: number;
  cantidadPedida: number;
  precioFinal: number;
  fechaFacturacion: string;
  usuario: string;
}

@Component({
  selector: 'app-orders',
  standalone: true,
  templateUrl: './orders.component.html',
  styleUrls: ['./orders.component.css'],
  imports: [CommonModule]
})
export class OrdersComponent {
  orders: Order[] = [
    { codigoPedido: 1, articulo: 'Papel A4 Campus 80g Azul', pvp: 6.65, cantidadPedida: 10, precioFinal: 66.5, fechaFacturacion: '2024-03-10', usuario: 'juanperez' },
    { codigoPedido: 2, articulo: 'Bloc notas microperforado A5', pvp: 2.75, cantidadPedida: 15, precioFinal: 41.25, fechaFacturacion: '2024-03-12', usuario: 'mariagarcia' },
    { codigoPedido: 3, articulo: 'Bloc espiral tapa A4', pvp: 5.76, cantidadPedida: 8, precioFinal: 46.08, fechaFacturacion: '2024-03-14', usuario: 'carlossanchez' },
    { codigoPedido: 4, articulo: 'Bolsas Kraft Acolchadas Marrón', pvp: 3.39, cantidadPedida: 20, precioFinal: 67.8, fechaFacturacion: '2024-03-15', usuario: 'anafernandez' },
    { codigoPedido: 5, articulo: 'Etiquetas adhesivas Plus Office', pvp: 21.48, cantidadPedida: 5, precioFinal: 107.4, fechaFacturacion: '2024-03-17', usuario: 'pedrolopez' },
    { codigoPedido: 6, articulo: 'Bloc Campus Espiral 80 Hojas', pvp: 4.93, cantidadPedida: 7, precioFinal: 34.51, fechaFacturacion: '2024-03-19', usuario: 'sandramartin' },
    { codigoPedido: 7, articulo: 'Papel A4 Campus 80g Blanco', pvp: 4.14, cantidadPedida: 12, precioFinal: 49.68, fechaFacturacion: '2024-03-21', usuario: 'luisrodriguez' },
    { codigoPedido: 8, articulo: 'Bloc Microperforado Campus A4', pvp: 5.05, cantidadPedida: 6, precioFinal: 30.3, fechaFacturacion: '2024-03-22', usuario: 'elenaramirez' },
    { codigoPedido: 9, articulo: 'Blocs notas Verde flúor', pvp: 1.52, cantidadPedida: 25, precioFinal: 38, fechaFacturacion: '2024-03-23', usuario: 'javiergomez' },
    { codigoPedido: 10, articulo: 'Sobres C4 Makro Paper', pvp: 4.22, cantidadPedida: 10, precioFinal: 42.2, fechaFacturacion: '2024-03-24', usuario: 'robertohernandez' },
    { codigoPedido: 11, articulo: 'Papel A4 Campus 80g Amarillo', pvp: 6.65, cantidadPedida: 5, precioFinal: 33.25, fechaFacturacion: '2024-03-25', usuario: 'luciaflores' },
    { codigoPedido: 12, articulo: 'Bloc espiral tapa dura', pvp: 4.33, cantidadPedida: 9, precioFinal: 38.97, fechaFacturacion: '2024-03-26', usuario: 'sergioalonso' },
    { codigoPedido: 13, articulo: 'Blocs notas Amarillo flúor', pvp: 1.52, cantidadPedida: 30, precioFinal: 45.6, fechaFacturacion: '2024-03-27', usuario: 'martagonzalez' },
    { codigoPedido: 14, articulo: 'Bloc espiral tapa A5', pvp: 2.04, cantidadPedida: 12, precioFinal: 24.48, fechaFacturacion: '2024-03-28', usuario: 'pablojimenez' },
    { codigoPedido: 15, articulo: 'Bolsas acolchadas Kraft', pvp: 1.09, cantidadPedida: 40, precioFinal: 43.6, fechaFacturacion: '2024-03-29', usuario: 'sofiatorres' },
    { codigoPedido: 16, articulo: 'Papel A4 Campus 80g Naranja', pvp: 6.65, cantidadPedida: 10, precioFinal: 66.5, fechaFacturacion: '2024-03-30', usuario: 'adrianfernandez' },
    { codigoPedido: 17, articulo: 'Bloc Campus Espiral 50 Hojas', pvp: 3.29, cantidadPedida: 7, precioFinal: 23.03, fechaFacturacion: '2024-03-31', usuario: 'monicacruz' },
    { codigoPedido: 18, articulo: 'Etiquetas adhesivas Plus Office', pvp: 21.48, cantidadPedida: 3, precioFinal: 64.44, fechaFacturacion: '2024-04-01', usuario: 'davidmartin' },
    { codigoPedido: 19, articulo: 'Bloc espiral tapa básica', pvp: 2.04, cantidadPedida: 14, precioFinal: 28.56, fechaFacturacion: '2024-04-02', usuario: 'alejandragomez' },
    { codigoPedido: 20, articulo: 'Bloc espiral tapa blanda', pvp: 3.00, cantidadPedida: 6, precioFinal: 18, fechaFacturacion: '2024-04-03', usuario: 'franciscoramos' },
    { codigoPedido: 21, articulo: 'Bloc espiral tapa A4', pvp: 5.76, cantidadPedida: 9, precioFinal: 51.84, fechaFacturacion: '2024-04-04', usuario: 'lauravelazquez' },
    { codigoPedido: 22, articulo: 'Bloc notas microperforado A6', pvp: 1.56, cantidadPedida: 22, precioFinal: 34.32, fechaFacturacion: '2024-04-05', usuario: 'victorperez' },
    { codigoPedido: 23, articulo: 'Bolsas Kraft Acolchadas Marrón', pvp: 3.39, cantidadPedida: 12, precioFinal: 40.68, fechaFacturacion: '2024-04-06', usuario: 'claragutierrez' },
    { codigoPedido: 24, articulo: 'Bloc Microperforado Campus A4', pvp: 5.05, cantidadPedida: 5, precioFinal: 25.25, fechaFacturacion: '2024-04-07', usuario: 'gabrielsantos' },
    { codigoPedido: 25, articulo: 'Blocs notas Verde flúor', pvp: 1.52, cantidadPedida: 35, precioFinal: 53.2, fechaFacturacion: '2024-04-08', usuario: 'isabelgomez' },
  ];

  itemsPerPage = 10;
  currentPage = signal(1);

  get totalPages(): number {
    return Math.ceil(this.orders.length / this.itemsPerPage);
  }

  getCurrentPageItems(): Order[] {
    const startIndex = (this.currentPage() - 1) * this.itemsPerPage;
    return this.orders.slice(startIndex, startIndex + this.itemsPerPage);
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage.set(page);
    }
  }
}
