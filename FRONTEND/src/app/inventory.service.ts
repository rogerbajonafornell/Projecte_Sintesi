import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

export interface InventoryItem {
  CodigoArticulo: number;
  DescripcionArticulo: string;
  PVP: number;
  Unidades: number;
}

@Injectable({ providedIn: 'root' })
export class InventoryService {
  constructor(private http: HttpClient) {}

  getInventory() {
    return this.http.get<InventoryItem[]>('http://localhost:8000/api/inventari/articles/');
  }
}
