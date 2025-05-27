import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InventoryService, Article } from '../../inventory.service';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { FormsModule } from '@angular/forms';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [CommonModule, TranslateModule, FormsModule],
  templateUrl: './inventory.component.html',
  styleUrl: './inventory.component.css',
})
export class InventoryComponent {
  private inventoryService = inject(InventoryService);
  private translate = inject(TranslateService);

  // Llista d'articles i control de pàgina
  inventory = signal<Article[]>([]);
  itemsPerPage = 10;
  currentPage = signal(1);

  // Estat d'edició
  editingItem = signal<Article | null>(null);
  editValidationErrors: any = {};

  // Estat de creació
  addingNewItem: boolean = false;
  newItem = { DescripcionArticulo: '', PVP: null, Unidades: null };
  validationErrors: any = {};
  errorMessage: string = '';

  // Filtres
  searchTerm: string = '';
  minPrice: number | null = null;
  maxPrice: number | null = null;

  // Constructor: carrega dades inicials i subscripció a canvis d’idioma
  constructor() {
    this.inventoryService.getArticles().subscribe((data) => {
      this.inventory.set(data);
    });
  }

  // Retorna els elements de la pàgina actual amb filtres aplicats
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

  // Calcula el nombre total de pàgines amb filtres aplicats
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

  // Canvia de pàgina si és dins del rang
  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage.set(page);
    }
  }

  // Reinicia els filtres
  clearFilters() {
    this.searchTerm = '';
    this.minPrice = null;
    this.maxPrice = null;
    this.currentPage.set(1);
  }

  // Inicia el formulari per afegir un nou article
  startAddingNewItem() {
    this.addingNewItem = true;
    this.newItem = { DescripcionArticulo: '', PVP: null, Unidades: null };
    this.validationErrors = {};
    this.errorMessage = '';
  }

  // Cancel·la l’alta d’un nou article
  cancelNewItem() {
    this.addingNewItem = false;
    this.newItem = { DescripcionArticulo: '', PVP: null, Unidades: null };
    this.validationErrors = {};
    this.errorMessage = '';
  }

  // Afegeix un nou article si les validacions són correctes
  addItem() {
  this.validationErrors = {};
  this.errorMessage = '';

  // Validació dels camps
  if (!this.newItem.DescripcionArticulo?.trim()) {
    this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
      this.validationErrors.DescripcionArticulo = msg
    );
  }

  if (this.newItem.PVP === null || isNaN(this.newItem.PVP)) {
    this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
      this.validationErrors.PVP = msg
    );
  } else if (this.newItem.PVP <= 0) {
    this.translate.get('ERRORS.POSITIVE_NUMBER').subscribe(msg =>
      this.validationErrors.PVP = msg
    );
  }

  if (this.newItem.Unidades === null || isNaN(this.newItem.Unidades)) {
    this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
      this.validationErrors.Unidades = msg
    );
  } else if (this.newItem.Unidades < 0) {
    this.translate.get('ERRORS.NON_NEGATIVE_NUMBER').subscribe(msg =>
      this.validationErrors.Unidades = msg
    );
  }

  if (Object.keys(this.validationErrors).length > 0) {
    this.translate.get('ERRORS.SOLVE_ERRORS').subscribe(msg =>
      this.errorMessage = msg
    );
    return;
  }

  const articleData = {
    DescripcionArticulo: this.newItem.DescripcionArticulo!,
    PVP: this.newItem.PVP!,
    Unidades: this.newItem.Unidades!,
  };

  // Envia a l’API
  this.inventoryService.addArticle(articleData).subscribe({
    next: (createdArticle) => {
      this.inventory.set([createdArticle, ...this.inventory()]);
      this.cancelNewItem();
      Swal.fire(
        this.translate.instant('ADD_CONFIRMATION.SUCCESS_TITLE'),
        this.translate.instant('ADD_CONFIRMATION.SUCCESS_TEXT'),
        'success'
      );
    },
    error: (err) => {
      console.error(err);
      Swal.fire(
        this.translate.instant('ADD_CONFIRMATION.ERROR_TITLE'),
        this.translate.instant('ADD_CONFIRMATION.ERROR_TEXT'),
        'error'
      );
    }
  });
  }


  // Elimina un article per codi
  deleteItem(codigo: number) {
    Swal.fire({
      title: this.translate.instant('DELETE_CONFIRMATION.TITLE'),
      text: this.translate.instant('DELETE_CONFIRMATION.TEXT'),
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: this.translate.instant('DELETE_CONFIRMATION.CONFIRM_BUTTON'),
      cancelButtonText: this.translate.instant('DELETE_CONFIRMATION.CANCEL_BUTTON')
    }).then((result) => {
      if (result.isConfirmed) {
        this.inventoryService.deleteArticle(codigo).subscribe({
          next: () => {
            this.inventory.set(this.inventory().filter(item => item.CodigoArticulo !== codigo));
            Swal.fire(
              this.translate.instant('DELETE_CONFIRMATION.SUCCESS_TITLE'),
              this.translate.instant('DELETE_CONFIRMATION.SUCCESS_TEXT'),
              'success'
            );
          },
          error: (err) => {
            Swal.fire(
              this.translate.instant('DELETE_CONFIRMATION.ERROR_TITLE'),
              this.translate.instant('DELETE_CONFIRMATION.ERROR_TEXT'),
              'error'
            );
          }
        });
      }
    });
  }

  // Entra en mode edició per un article
  editItem(item: Article) {
    this.editingItem.set({ ...item });
  }

  // Desa els canvis d’un article editat si passa la validació
  saveEdit(edited: Article) {
  this.editValidationErrors = {};
  this.errorMessage = '';

  // Validació
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

  if (edited.Unidades === null || isNaN(edited.Unidades)) {
    this.translate.get('ERRORS.REQUIRED').subscribe(msg =>
      this.editValidationErrors.Unidades = msg
    );
  } else if (edited.Unidades < 0) {
    this.translate.get('ERRORS.NON_NEGATIVE_NUMBER').subscribe(msg =>
      this.editValidationErrors.Unidades = msg
    );
  }

  if (Object.keys(this.editValidationErrors).length > 0) {
    this.translate.get('ERRORS.SOLVE_ERRORS').subscribe(msg =>
      this.errorMessage = msg
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

      Swal.fire(
        this.translate.instant('EDIT_CONFIRMATION.SUCCESS_TITLE'),
        this.translate.instant('EDIT_CONFIRMATION.SUCCESS_TEXT'),
        'success'
      );
    },
    error: (err) => {
      console.error(err);
      Swal.fire(
        this.translate.instant('EDIT_CONFIRMATION.ERROR_TITLE'),
        this.translate.instant('EDIT_CONFIRMATION.ERROR_TEXT'),
        'error'
      );
    }
  });
  }


  // Cancel·la l’edició d’un article
  cancelEdit() {
    this.editingItem.set(null);
    this.editValidationErrors = {};
    this.errorMessage = '';
  }
}
