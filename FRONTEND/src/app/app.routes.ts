import { Routes } from '@angular/router';
import { InventoryComponent } from './pages/inventory/inventory.component';
import { OrdersComponent } from './pages/orders/orders.component';
import { HomeComponent } from './home/home.component';
import { UsersComponent } from './pages/users/users.component';
import { AuthGuard } from './auth.guard';
import { LoginComponent } from './login/login.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'home', component: HomeComponent, canActivate: [AuthGuard] },
  { path: 'inventory', component: InventoryComponent, canActivate: [AuthGuard] },
  { path: 'orders', component: OrdersComponent, canActivate: [AuthGuard] },
  { path: 'users', component: UsersComponent, canActivate: [AuthGuard] },

  { path: '', redirectTo: '/home', pathMatch: 'full' },
  { path: '**', redirectTo: '/home' }, // Fallback
];