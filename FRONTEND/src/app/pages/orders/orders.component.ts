import { Component, signal, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InventoryService, Comanda } from '../../inventory.service';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { FormsModule } from '@angular/forms';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-orders',
  standalone: true,
  templateUrl: './orders.component.html',
  styleUrls: ['./orders.component.css'],
  imports: [CommonModule, TranslateModule, FormsModule]
})
export class OrdersComponent {
  private inventoryService = inject(InventoryService);
  private translate = inject(TranslateService);

  orders = signal<Comanda[]>([]);

  itemsPerPage = 10;
  currentPage = signal(1);

  searchTerm: string = '';
  searchField: string = 'ComandaId';

  searchFields = [
    { key: 'ComandaId', label: 'GENERAL.CODE' },
    { key: 'Article.DescripcionArticulo', label: 'ORDERS.ARTICLE' },
    { key: 'User.FirstName', label: 'ORDERS.USER' }
  ];

  constructor() {
    this.inventoryService.getComandes().subscribe((data) => {
      this.orders.set(data);
    });
  }

  // Filtrado y paginación
  getCurrentPageItems(): Comanda[] {
    let filtered = this.orders();

    if (this.searchTerm.trim()) {
      const value = this.searchTerm.toLowerCase();
      switch (this.searchField) {
        case 'ComandaId':
          filtered = filtered.filter(o => o.ComandaId.toString().includes(value));
          break;
        case 'Article.DescripcionArticulo':
          filtered = filtered.filter(o =>
            o.Article?.DescripcionArticulo?.toLowerCase().includes(value)
          );
          break;
        case 'User.FirstName':
          filtered = filtered.filter(o =>
            o.User?.FirstName?.toLowerCase().includes(value)
          );
          break;
      }
    }

    const start = (this.currentPage() - 1) * this.itemsPerPage;
    return filtered.slice(start, start + this.itemsPerPage);
  }

  get totalPages(): number {
    let filtered = this.orders();

    if (this.searchTerm.trim()) {
      const value = this.searchTerm.toLowerCase();
      switch (this.searchField) {
        case 'ComandaId':
          filtered = filtered.filter(o => o.ComandaId.toString().includes(value));
          break;
        case 'Article.DescripcionArticulo':
          filtered = filtered.filter(o =>
            o.Article?.DescripcionArticulo?.toLowerCase().includes(value)
          );
          break;
        case 'User.FirstName':
          filtered = filtered.filter(o =>
            o.User?.FirstName?.toLowerCase().includes(value)
          );
          break;
      }
    }

    return Math.ceil(filtered.length / this.itemsPerPage) || 1;
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage.set(page);
    }
  }

  clearFilters() {
    this.searchTerm = '';
    this.searchField = 'ComandaId';
    this.currentPage.set(1);
  }

  deleteItem(codigo: number) {
  Swal.fire({
    title: this.translate.instant('DELETE_ORDER_CONFIRMATION.TITLE'),
    text: this.translate.instant('DELETE_ORDER_CONFIRMATION.TEXT'),
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#d33',
    cancelButtonColor: '#3085d6',
    confirmButtonText: this.translate.instant('DELETE_ORDER_CONFIRMATION.CONFIRM_BUTTON'),
    cancelButtonText: this.translate.instant('DELETE_ORDER_CONFIRMATION.CANCEL_BUTTON')
  }).then((result) => {
    if (result.isConfirmed) {
      this.inventoryService.deleteOrder(codigo).subscribe({
        next: () => {
          this.orders.set(this.orders().filter(item => item.ComandaId !== codigo));
          Swal.fire(
            this.translate.instant('DELETE_ORDER_CONFIRMATION.SUCCESS_TITLE'),
            this.translate.instant('DELETE_ORDER_CONFIRMATION.SUCCESS_TEXT'),
            'success'
          );
        },
        error: (err) => {
          console.error('Error eliminando pedido', err);
          Swal.fire(
            this.translate.instant('DELETE_ORDER_CONFIRMATION.ERROR_TITLE'),
            this.translate.instant('DELETE_ORDER_CONFIRMATION.ERROR_TEXT'),
            'error'
          );
        }
      });
    }
  });
}
}
