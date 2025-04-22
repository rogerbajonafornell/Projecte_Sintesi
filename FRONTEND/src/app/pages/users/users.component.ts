import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [CommonModule], // ✅ Importar CommonModule para *ngFor
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.css']
})
export class UsersComponent {
  users = [
    { username: "JuanPerez", phone: "123-456-7890" },
    { username: "MariaLopez", phone: "987-654-3210" },
    { username: "CarlosGarcia", phone: "555-123-4567" },
    { username: "AnaMartinez", phone: "444-567-8901" },
    { username: "PedroGomez", phone: "222-345-6789" },
    { username: "LauraDiaz", phone: "666-789-0123" },
    { username: "LuisFernandez", phone: "111-222-3333" },
    { username: "SofiaRamirez", phone: "777-888-9999" },
    { username: "DavidHernandez", phone: "888-999-0000" },
    { username: "ElenaTorres", phone: "999-000-1111" }
  ];

  currentPage = 1;
  itemsPerPage = 5;

  get totalPages(): number {
    return Math.ceil(this.users.length / this.itemsPerPage);
  }

  getCurrentPageItems() {
    const start = (this.currentPage - 1) * this.itemsPerPage;
    return this.users.slice(start, start + this.itemsPerPage);
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
    }
  }
}
