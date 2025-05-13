import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslateModule],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent {
  private translate = inject(TranslateService);
  translatedTitle = signal<string>('');
  private langSub: Subscription;

  constructor() {
    this.loadTranslations();
    this.langSub = this.translate.onLangChange.subscribe(() => {
      this.loadTranslations();
    });
  
  }

  loadTranslations() {
    this.translate.get('ORDERS.TITLE').subscribe((res: string) => {
      this.translatedTitle.set(res);
    });
  }

  ngOnDestroy() {
    this.langSub?.unsubscribe();
  }
}
