import { ApplicationConfig } from '@angular/core';
import { provideRouter, Routes } from '@angular/router';
import { InventoryComponent } from './pages/inventory/inventory.component';
import { OrdersComponent } from './pages/orders/orders.component';

const routes: Routes = [
  { path: 'inventory', component: InventoryComponent },
  { path: 'orders', component: OrdersComponent },
  { path: '', redirectTo: '/inventory', pathMatch: 'full' }, // Default page
];

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
  ]
};
