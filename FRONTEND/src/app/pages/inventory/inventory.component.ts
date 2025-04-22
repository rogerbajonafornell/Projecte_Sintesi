import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

interface InventoryItem {
  CodigoArticulo: number;
  DescripcionArticulo: string;
  PVP: number;
  Unidades: number;
}

@Component({
  selector: 'app-inventory',
  imports: [CommonModule],
  templateUrl: './inventory.component.html',
  styleUrl: './inventory.component.css'
})
export class InventoryComponent {
  inventory: InventoryItem[] = [
    { CodigoArticulo: 1002, DescripcionArticulo: 'Papel A4 Campus 80g Azul', PVP: 6.65, Unidades: 1976 },
    { CodigoArticulo: 1019, DescripcionArticulo: 'Papel A4 Campus 80g blanco', PVP: 4.14, Unidades: 479 },
    { CodigoArticulo: 1113, DescripcionArticulo: 'Bloc notas microperforado A5', PVP: 2.75, Unidades: 1827 },
    { CodigoArticulo: 1114, DescripcionArticulo: 'Bloc notas microperforado A6', PVP: 1.56, Unidades: 2553 },
    { CodigoArticulo: 1116, DescripcionArticulo: 'Bloc Microperforado Campus A4', PVP: 5.05, Unidades: 679 },
    { CodigoArticulo: 1137, DescripcionArticulo: 'Bloc espiral tapa A4', PVP: 5.76, Unidades: 2111 },
    { CodigoArticulo: 1142, DescripcionArticulo: 'Bloc espiral tapa blanda', PVP: 3.00, Unidades: 1965 },
    { CodigoArticulo: 1143, DescripcionArticulo: 'Bloc espiral tapa básica', PVP: 2.04, Unidades: 2086 },
    { CodigoArticulo: 1148, DescripcionArticulo: 'Bloc espiral tapa A5', PVP: 2.04, Unidades: 2346 },
    { CodigoArticulo: 1156, DescripcionArticulo: 'Bloc espiral tapa dura', PVP: 4.33, Unidades: 294 },
    { CodigoArticulo: 1208, DescripcionArticulo: 'Blocs notas Amarillo flúor', PVP: 1.52, Unidades: 1557 },
    { CodigoArticulo: 1209, DescripcionArticulo: 'Blocs notas Verde flúor', PVP: 1.52, Unidades: 413 },
    { CodigoArticulo: 1351, DescripcionArticulo: 'Bolsas Kraft Acolchadas Marrón', PVP: 3.39, Unidades: 814 },
    { CodigoArticulo: 1599, DescripcionArticulo: 'Bloc Campus Espiral 80 Hojas', PVP: 4.93, Unidades: 208 },
    { CodigoArticulo: 1634, DescripcionArticulo: 'Etiquetas adhesivas Plus Office', PVP: 21.48, Unidades: 2207 },
    { CodigoArticulo: 1846, DescripcionArticulo: 'Bolsas acolchadas Kraft', PVP: 1.09, Unidades: 868 },
    { CodigoArticulo: 2380, DescripcionArticulo: 'Sobres C4 Makro Paper', PVP: 4.22, Unidades: 2345 },
    { CodigoArticulo: 2549, DescripcionArticulo: 'Bloc Campus Espiral 50 Hojas', PVP: 3.29, Unidades: 631 },
    { CodigoArticulo: 2891, DescripcionArticulo: 'Papel A4 Campus 80g Naranja', PVP: 6.65, Unidades: 973 },
    { CodigoArticulo: 2892, DescripcionArticulo: 'Papel A4 Campus 80g Amarillo', PVP: 6.65, Unidades: 2148 },
  ];

  itemsPerPage = 10;
  currentPage = signal(1);

  get totalPages(): number {
    return Math.ceil(this.inventory.length / this.itemsPerPage);
  }

  getCurrentPageItems(): InventoryItem[] {
    const startIndex = (this.currentPage() - 1) * this.itemsPerPage;
    return this.inventory.slice(startIndex, startIndex + this.itemsPerPage);
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage.set(page);
    }
  }
}
