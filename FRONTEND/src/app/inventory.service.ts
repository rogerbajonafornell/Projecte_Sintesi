import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../environments/environment';

export interface InventoryItem {
  CodigoArticulo: number;
  DescripcionArticulo: string;
  PVP: number;
  Unidades: number;
}

@Injectable({ providedIn: 'root' })
export class InventoryService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getInventory() {
    return this.http.get<InventoryItem[]>(`${this.apiUrl}/api/inventari/articles/`);
  }
}
