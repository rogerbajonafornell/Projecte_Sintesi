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

  constructor() {
    this.inventoryService.getArticles().subscribe((data) => {
      console.log(data);
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

  getCurrentPageItems(): Article[] {
    const start = (this.currentPage() - 1) * this.itemsPerPage;
    return this.inventory().slice(start, start + this.itemsPerPage);
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage.set(page);
    }
  }

  addingNewItem: boolean = false;
  newItem = { DescripcionArticulo: '', PVP: null, Unidades: null };
  validationErrors: any = {};
  errorMessage: string = '';

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
      this.validationErrors.DescripcionArticulo = true;
    }
    if (this.newItem.PVP == null || this.newItem.PVP <= 0) {
      this.validationErrors.PVP = true;
    }
    if (this.newItem.Unidades == null || this.newItem.Unidades < 0) {
      this.validationErrors.Unidades = true;
    }

    if (Object.keys(this.validationErrors).length > 0) {
      this.translate.get('FORM.VALIDATION_ERROR').subscribe(res => {
        this.errorMessage = res;
      });
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

  cancelEdit() {
    this.editingItem.set(null);
  }

  saveEdit(edited: Article) {
    // Aquí puedes enviar el cambio al backend
    this.inventoryService.updateArticle(edited).subscribe({
      next: () => {
        const updatedList = this.inventory().map(item =>
          item.CodigoArticulo === edited.CodigoArticulo ? edited : item
        );
        this.inventory.set(updatedList);
        this.editingItem.set(null);
      },
      error: (err) => {
        console.error('Error actualizando artículo', err);
      }
    });
  }

  ngOnDestroy() {
    this.langSub?.unsubscribe();
  }
}
