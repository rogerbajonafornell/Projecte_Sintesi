import { TestBed } from '@angular/core/testing';

import { ProvaBackendService } from './prova-backend.service';

describe('ProvaBackendService', () => {
  let service: ProvaBackendService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ProvaBackendService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
