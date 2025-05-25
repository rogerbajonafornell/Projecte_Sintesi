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
  // Injecció dels serveis
  private inventoryService = inject(InventoryService);
  private translate = inject(TranslateService);

  // Estat reactiu per la llista de comandes
  orders = signal<Comanda[]>([]);

  // Control de paginació
  itemsPerPage = 10;
  currentPage = signal(1);

  // Títol traduït
  translatedTitle = signal<string>('');

  // Subscripció per gestionar canvis d'idioma
  private langSub: Subscription;

  constructor() {
    // Obté les comandes des del servei
    this.inventoryService.getComandes().subscribe((data) => {
      this.orders.set(data);
    });

    // Carrega la traducció inicial
    this.loadTranslations();

    // Recarrega la traducció si canvia l'idioma
    this.langSub = this.translate.onLangChange.subscribe(() => {
      this.loadTranslations();
    });
  }

  // Carrega la traducció del títol
  loadTranslations() {
    this.translate.get('ORDERS.TITLE').subscribe((res: string) => {
      this.translatedTitle.set(res);
    });
  }

  // Calcula el total de pàgines segons la quantitat de comandes
  get totalPages(): number {
    return Math.ceil(this.orders().length / this.itemsPerPage);
  }

  // Retorna les comandes de la pàgina actual
  getCurrentPageItems(): Comanda[] {
    const startIndex = (this.currentPage() - 1) * this.itemsPerPage;
    return this.orders().slice(startIndex, startIndex + this.itemsPerPage);
  }

  // Canvia a una pàgina determinada
  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage.set(page);
    }
  }

  // Elimina una comanda amb confirmació
  deleteItem(codigo: number) {
    if (confirm('¿Estás seguro de que deseas eliminar este artículo?')) {
      this.inventoryService.deleteOrder(codigo).subscribe({
        next: () => {
          // Actualitza la llista localment després de l'eliminació
          this.orders.set(this.orders().filter(item => item.ComandaId !== codigo));
        },
        error: (err) => {
          console.error('Error eliminando artículo', err);
        }
      });
    }
  }

  // Neteja la subscripció en destruir el component
  ngOnDestroy() {
    this.langSub?.unsubscribe();
  }
}
