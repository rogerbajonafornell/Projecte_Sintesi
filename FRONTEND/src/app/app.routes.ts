import { Routes } from '@angular/router';
import { InventoryComponent } from './pages/inventory/inventory.component';
import { OrdersComponent } from './pages/orders/orders.component';
import { HomeComponent } from './home/home.component';
import { UsersComponent } from './pages/users/users.component';

export const routes: Routes = [
  { path: 'home', component: HomeComponent },
  { path: 'inventory', component: InventoryComponent },
  { path: 'orders', component: OrdersComponent },
  { path: 'users', component: UsersComponent },
  { path: '', redirectTo: '/home', pathMatch: 'full' }, // Página por defecto
];
