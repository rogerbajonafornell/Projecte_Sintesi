import { Component, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InventoryItem, InventoryService } from '../../inventory.service';

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './inventory.component.html',
  styleUrl: './inventory.component.css',
})
export class InventoryComponent {
  private inventoryService = inject(InventoryService);

  inventory = signal<InventoryItem[]>([]);
  itemsPerPage = 10;
  currentPage = signal(1);

  constructor() {
    this.inventoryService.getInventory().subscribe((data) => {
      this.inventory.set(data);
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
}
