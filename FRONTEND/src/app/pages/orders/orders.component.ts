import { Component, signal, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InventoryService, Comanda } from '../../inventory.service';
import { TranslateModule } from '@ngx-translate/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-orders',
  standalone: true,
  templateUrl: './orders.component.html',
  styleUrls: ['./orders.component.css'],
  imports: [CommonModule, TranslateModule, FormsModule]
})
export class OrdersComponent {
  private inventoryService = inject(InventoryService);

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
    if (confirm('¿Estás seguro de que deseas eliminar este artículo?')) {
      this.inventoryService.deleteOrder(codigo).subscribe({
        next: () => {
          this.orders.set(this.orders().filter(item => item.ComandaId !== codigo));
        },
        error: (err) => {
          console.error('Error eliminando artículo', err);
        }
      });
    }
  }
}
