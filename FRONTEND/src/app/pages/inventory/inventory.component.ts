import { Component, signal, computed, inject, effect, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InventoryService, Article, Comanda, Usuari } from '../../inventory.service';
import { TranslateModule, TranslateService, LangChangeEvent } from '@ngx-translate/core';
import { Subscription } from 'rxjs';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [CommonModule, TranslateModule, FormsModule],
  templateUrl: './inventory.component.html',
  styleUrl: './inventory.component.css',
})
export class InventoryComponent implements OnDestroy {
  private inventoryService = inject(InventoryService);
  private translate = inject(TranslateService);

  inventory = signal<Article[]>([]);
  itemsPerPage = 10;
  currentPage = signal(1);

  translatedTitle = signal<string>(''); // ejemplo de uso en código
  private langSub: Subscription;

  editingItem = signal<Article | null>(null);

  editValidationErrors: any = {};

  addingNewItem: boolean = false;
  newItem = { DescripcionArticulo: '', PVP: null, Unidades: null };
  validationErrors: any = {};
  errorMessage: string = '';

  searchTerm: string = '';
  minPrice: number | null = null;
  maxPrice: number | null = null;

  constructor() {
    this.inventoryService.getArticles().subscribe((data) => {
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

  getCurrentPageItems(): Article[] {
    let filtered = this.inventory();

    if (this.searchTerm.trim()) {
      filtered = filtered.filter(item =>
        item.DescripcionArticulo.toLowerCase().includes(this.searchTerm.toLowerCase())
      );
    }

    if (this.minPrice != null) {
      filtered = filtered.filter(item => item.PVP >= this.minPrice!);
    }

    if (this.maxPrice != null) {
      filtered = filtered.filter(item => item.PVP <= this.maxPrice!);
    }

    const start = (this.currentPage() - 1) * this.itemsPerPage;
    return filtered.slice(start, start + this.itemsPerPage);
  }

  get totalPages(): number {
    let filtered = this.inventory();

    if (this.searchTerm.trim()) {
      filtered = filtered.filter(item =>
        item.DescripcionArticulo.toLowerCase().includes(this.searchTerm.toLowerCase())
      );
    }

    if (this.minPrice != null) {
      filtered = filtered.filter(item => item.PVP >= this.minPrice!);
    }

    if (this.maxPrice != null) {
      filtered = filtered.filter(item => item.PVP <= this.maxPrice!);
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
    this.minPrice = null;
    this.maxPrice = null;
    this.currentPage.set(1);
  }

  startAddingNewItem() {
    this.addingNewItem = true;
    this.newItem = { DescripcionArticulo: '', PVP: null, Unidades: null };
    this.validationErrors = {};
    this.errorMessage = '';
  }

  cancelNewItem() {
    this.addingNewItem = false;
    this.newItem = { DescripcionArticulo: '', PVP: null, Unidades: null };
    this.validationErrors = {};
    this.errorMessage = '';
  }

  addItem() {
    this.validationErrors = {};
    this.errorMessage = '';

    // Validación
    if (!this.newItem.DescripcionArticulo?.trim()) {
      this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
        this.validationErrors.DescripcionArticulo = msg
      );
    }
    
    // Validar PVP
    if (this.newItem.PVP === null || this.newItem.PVP === '' || isNaN(this.newItem.PVP)) {
      this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
        this.validationErrors.PVP = msg
      );
    } else if (this.newItem.PVP <= 0) {
      this.translate.get('ERRORS.POSITIVE_NUMBER').subscribe(msg =>
        this.validationErrors.PVP = msg
      );
    }
    
    // Validar Unidades
    if (this.newItem.Unidades === null || this.newItem.Unidades === '' || isNaN(this.newItem.Unidades)) {
      this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
        this.validationErrors.Unidades = msg
      );
    } else if (this.newItem.Unidades < 0) {
      this.translate.get('ERRORS.NON_NEGATIVE_NUMBER').subscribe(msg =>
        this.validationErrors.Unidades = msg
      );
    }
    
  
    // Si hay errores, no continuar
    if (Object.keys(this.validationErrors).length > 0) {
      this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
        this.errorMessage = 'Por favor, corrige los errores antes de guardar.'
      );
      return;
    }

    const articleData = {
      DescripcionArticulo: this.newItem.DescripcionArticulo!,
      PVP: this.newItem.PVP!,
      Unidades: this.newItem.Unidades!,
    };

    this.inventoryService.addArticle(articleData).subscribe({
      next: (createdArticle) => {
        this.inventory.set([createdArticle, ...this.inventory()]);
        this.cancelNewItem();
      },
      error: (err) => {
        this.errorMessage = 'Error al guardar el artículo.';
        console.error(err);
      }
    });
  }

  deleteItem(codigo: number) {
    if (confirm('¿Estás seguro de que deseas eliminar este artículo?')) {
      this.inventoryService.deleteArticle(codigo).subscribe({
        next: () => {
          // Actualiza la lista localmente
          this.inventory.set(this.inventory().filter(item => item.CodigoArticulo !== codigo));
        },
        error: (err) => {
          console.error('Error eliminando artículo', err);
        }
      });
    }
  }

  editItem(item: Article) {
    this.editingItem.set({ ...item });
  }

  saveEdit(edited: Article) {
    this.editValidationErrors = {};
    this.errorMessage = '';
  
    if (!edited.DescripcionArticulo?.trim()) {
      this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
        this.editValidationErrors.DescripcionArticulo = msg
      );
    }
  
    if (edited.PVP === null || isNaN(edited.PVP)) {
      this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
        this.editValidationErrors.PVP = msg
      );
    } else if (edited.PVP <= 0) {
      this.translate.get('ERRORS.POSITIVE_NUMBER').subscribe(msg =>
        this.editValidationErrors.PVP = msg
      );
    }
  
    if (edited.Unidades === null ||  isNaN(edited.Unidades)) {
      this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
        this.editValidationErrors.Unidades = msg
      );
    } else if (edited.Unidades < 0) {
      this.translate.get('ERRORS.NON_NEGATIVE_NUMBER').subscribe(msg =>
        this.editValidationErrors.Unidades = msg
      );
    }
  
    if (Object.keys(this.editValidationErrors).length > 0) {
      this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
        this.errorMessage = 'Por favor, corrige los errores antes de guardar.'
      );
      return;
    }
  
    this.inventoryService.updateArticle(edited).subscribe({
      next: () => {
        const updatedList = this.inventory().map(item =>
          item.CodigoArticulo === edited.CodigoArticulo ? edited : item
        );
        this.inventory.set(updatedList);
        this.editingItem.set(null);
      },
      error: (err) => {
        this.errorMessage = 'Error actualizando el artículo.';
        console.error(err);
      }
    });
  }
  
  cancelEdit() {
    this.editingItem.set(null);
    this.editValidationErrors = {};
    this.errorMessage = '';
  }

  ngOnDestroy() {
    this.langSub?.unsubscribe();
  }
}
