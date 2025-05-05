import { Component, signal, computed, inject, effect, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InventoryItem, InventoryService } from '../../inventory.service';
import { TranslateModule, TranslateService, LangChangeEvent } from '@ngx-translate/core';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './inventory.component.html',
  styleUrl: './inventory.component.css',
})
export class InventoryComponent implements OnDestroy {
  private inventoryService = inject(InventoryService);
  private translate = inject(TranslateService);

  inventory = signal<InventoryItem[]>([]);
  itemsPerPage = 10;
  currentPage = signal(1);

  translatedTitle = signal<string>(''); // ejemplo de uso en código
  private langSub: Subscription;

  constructor() {
    this.inventoryService.getInventory().subscribe((data) => {
      this.inventory.set(data);
    });

    // Traducción inicial
    this.loadTranslations();

    // Suscribirse a cambios de idioma
    this.langSub = this.translate.onLangChange.subscribe(() => {
      this.loadTranslations();
    });
  }

  loadTranslations() {
    this.translate.get('INVENTORY.TITLE').subscribe((res: string) => {
      this.translatedTitle.set(res);
    });
  }

  get totalPages(): number {
    return Math.ceil(this.inventory().length / this.itemsPerPage);
  }

  getCurrentPageItems(): InventoryItem[] {
    const start = (this.currentPage() - 1) * this.itemsPerPage;
    return this.inventory().slice(start, start + this.itemsPerPage);
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage.set(page);
    }
  }

  ngOnDestroy() {
    this.langSub?.unsubscribe();
  }
}
