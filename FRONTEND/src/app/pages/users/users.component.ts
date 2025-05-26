import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { InventoryService, Usuari } from '../../inventory.service';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.css']
})
export class UsersComponent {
  // Injecció dels serveis
  private inventoryService = inject(InventoryService);

  // Llista d'usuaris obtinguda del servei
  users = signal<Usuari[]>([]);

  // Control de pàgina i nombre d'elements per pàgina
  currentPage = signal(1);
  itemsPerPage = 5;

  constructor() {
    // Carrega inicial dels usuaris
    this.inventoryService.getUsuaris().subscribe((data) => {
      this.users.set(data);
    });
  }

  // Calcula el nombre total de pàgines en funció del nombre d'usuaris
  get totalPages(): number {
    return Math.ceil(this.users().length / this.itemsPerPage);
  }

  // Retorna els usuaris corresponents a la pàgina actual
  getCurrentPageItems(): Usuari[] {
    const start = (this.currentPage() - 1) * this.itemsPerPage;
    return this.users().slice(start, start + this.itemsPerPage);
  }

  // Canvia a una pàgina específica
  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage.set(page);
    }
  }
}
