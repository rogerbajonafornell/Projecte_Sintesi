import { Component, signal, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InventoryService, Comanda } from '../../inventory.service';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-orders',
  standalone: true,
  templateUrl: './orders.component.html',
  styleUrls: ['./orders.component.css'],
  imports: [CommonModule, TranslateModule]
})
export class OrdersComponent implements OnDestroy {
  private inventoryService = inject(InventoryService);
  private translate = inject(TranslateService);

  orders = signal<Comanda[]>([]);
  itemsPerPage = 10;
  currentPage = signal(1);
  translatedTitle = signal<string>('');
  private langSub: Subscription;

  constructor() {
    this.inventoryService.getComandes().subscribe((data) => {
      console.log(data);
      this.orders.set(data);
    });

    this.loadTranslations();
    this.langSub = this.translate.onLangChange.subscribe(() => {
      this.loadTranslations();
    });
  }

  loadTranslations() {
    this.translate.get('ORDERS.TITLE').subscribe((res: string) => {
      this.translatedTitle.set(res);
    });
  }

  get totalPages(): number {
    return Math.ceil(this.orders().length / this.itemsPerPage);
  }

  getCurrentPageItems(): Comanda[] {
    const startIndex = (this.currentPage() - 1) * this.itemsPerPage;
    return this.orders().slice(startIndex, startIndex + this.itemsPerPage);
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage.set(page);
    }
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

  ngOnDestroy() {
    this.langSub?.unsubscribe();
  }
}
