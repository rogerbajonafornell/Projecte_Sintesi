import { Component, signal, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { InventoryService, Usuari } from '../../inventory.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.css']
})
export class UsersComponent implements OnDestroy {
  private inventoryService = inject(InventoryService);
  private translate = inject(TranslateService);

  users = signal<Usuari[]>([]);
  currentPage = signal(1);
  itemsPerPage = 5;

  translatedTitle = signal<string>('');
  private langSub: Subscription;

  constructor() {
    this.inventoryService.getUsuaris().subscribe((data) => {
      this.users.set(data);
    });

    this.loadTranslations();

    this.langSub = this.translate.onLangChange.subscribe(() => {
      this.loadTranslations();
    });
  }

  loadTranslations() {
    this.translate.get('USERS.TITLE').subscribe((res: string) => {
      this.translatedTitle.set(res);
    });
  }

  get totalPages(): number {
    return Math.ceil(this.users().length / this.itemsPerPage);
  }

  getCurrentPageItems(): Usuari[] {
    const start = (this.currentPage() - 1) * this.itemsPerPage;
    return this.users().slice(start, start + this.itemsPerPage);
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage.set(page);
    }
  }

  ngOnDestroy() {
    this.langSub?.unsubscribe();
  }
}
