import { AfterViewInit, Component, OnDestroy, OnInit, TemplateRef, ViewChild } from '@angular/core';
import { MapControl, MapLayerGroup, MapService } from "../../../map/map.service";
import {
  Area,
  AreaLevel,
  Population,
  Year,
  Prognosis,
  Gender,
  AgeGroup, PopEntry, DemandRateSet, LogEntry
} from "../../../rest-interfaces";
import { InputCardComponent } from "../../../dash/input-card.component";
import { SelectionModel } from "@angular/cdk/collections";
import { SettingsService } from "../../../settings.service";
import { RestAPI } from "../../../rest-api";
import { HttpClient } from "@angular/common/http";
import { RemoveDialogComponent } from "../../../dialogs/remove-dialog/remove-dialog.component";
import { MatDialog } from "@angular/material/dialog";
import { PopulationService } from "../../population/population.service";
import { showAPIError, sortBy } from "../../../helpers/utils";
import { AgeTreeComponent, AgeTreeData } from "../../../diagrams/age-tree/age-tree.component";
import { FormBuilder, FormControl, FormGroup } from "@angular/forms";
import { ConfirmDialogComponent } from "../../../dialogs/confirm-dialog/confirm-dialog.component";
import { BehaviorSubject, Subscription } from "rxjs";
import * as fileSaver from "file-saver-es";
import { SimpleDialogComponent } from "../../../dialogs/simple-dialog/simple-dialog.component";
import { VectorLayer } from "../../../map/layers";

@Component({
  selector: 'app-prognosis-data',
  templateUrl: './prognosis-data.component.html',
  styleUrls: ['./prognosis-data.component.scss','../real-data/real-data.component.scss']
})
export class PrognosisDataComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('yearCard') yearCard?: InputCardComponent;
  @ViewChild('ageTree') ageTree?: AgeTreeComponent;
  @ViewChild('propertiesEdit') propertiesEdit?: TemplateRef<any>;
  @ViewChild('propertiesCard') propertiesCard?: InputCardComponent;
  @ViewChild('dataTemplate') dataTemplate?: TemplateRef<any>;
  @ViewChild('fileUploadTemplate') fileUploadTemplate?: TemplateRef<any>;
  isLoading$ = new BehaviorSubject<boolean>(true);
  isProcessing$ = new BehaviorSubject<boolean>(true);
  mapControl?: MapControl;
  layerGroup?: MapLayerGroup;
  activePrognosis?: Prognosis;
  genders: Gender[] = [];
  ageGroups: AgeGroup[] = [];
  years: Year[] = [];
  yearSelection = new SelectionModel<number>(true);
  prognoses: Prognosis[] = [];
  prognosisYears: number[] = [];
  populations: Population[] = [];
  popLevel?: AreaLevel;
  popEntries: Record<number, PopEntry[]> = {};
  defaultPopLevel?: AreaLevel;
  areas: Area[] = [];
  previewYear?: Year;
  previewArea?: Area;
  previewLayer?: VectorLayer;
  dataColumns: string[] = [];
  dataRows: any[][] = [];
  dataYear?: Year;
  propertiesForm: FormGroup;
  file?: File;
  subscriptions: Subscription[] = [];

  constructor(private mapService: MapService, private settings: SettingsService, private dialog: MatDialog,
              private rest: RestAPI, private http: HttpClient, public popService: PopulationService, private formBuilder: FormBuilder) {
    // make sure data requested here is up-to-date
    this.popService.reset();
    this.propertiesForm = this.formBuilder.group({
      name: new FormControl(''),
      description: new FormControl('')
    });
    this.isLoading$.next(true);
  }

  // ToDo: shares a lot of Code with real-data-component, at least the map view should be seperated into reusable view
  ngOnInit(): void {
    this.mapControl = this.mapService.get('base-prog-data-map');
    this.layerGroup = this.mapControl.addGroup('Bevölkerungsentwicklung (Prognose)', { order: -1 });
    this.popService.getAreaLevels({ reset: true }).subscribe(areaLevels => {
      this.defaultPopLevel = areaLevels.find(al => al.isDefaultPopLevel);
      this.popLevel = areaLevels.find(al => al.isPopLevel);
      this.isLoading$.next(false);
      if (this.popLevel) {
        this.popService.getAreas(this.popLevel.id, { reset: true }).subscribe(areas => this.areas = areas);
      }
    })
    this.subscriptions.push(this.settings.baseDataSettings$.subscribe(baseSettings => {
      this.isProcessing$.next(baseSettings.processes?.population || false);
    }));
    this.settings.fetchBaseDataSettings();
    this.fetchData();
  }

  ngAfterViewInit() {
    this.setupYearCard();
    this.setupPropertiesCard();
  }

  fetchData(): void {
    this.previewYear = undefined;
    this.previewArea = undefined;
    this.ageTree?.clear();
    this.updatePreview();
    this.dataColumns = ['Gebiet']
    this.popService.getGenders().subscribe(genders => {
      this.genders = genders;
      this.popService.getAgeGroups().subscribe(ageGroups => {
        this.genders.forEach(gender => {
          this.dataColumns = this.dataColumns.concat(ageGroups.map(ag => `${ag.label} (${gender.name})`));
        })
        this.ageGroups = sortBy(ageGroups, 'fromAge');
        this.http.get<Year[]>(this.rest.URLS.years).subscribe(years => {
          this.years = [];
          this.prognosisYears = [];
          years.forEach(year => {
            if (year.isPrognosis) {
              this.prognosisYears.push(year.year);
            }
            this.years.push(year);
          })
          this.popService.fetchPopulations(true).subscribe(populations => {
            this.populations = populations;
            this.popService.fetchPrognoses().subscribe(prognoses => this.prognoses = prognoses);
          });
        });
      })
    });
  }

  onPrognosisChange() {
    // this.previewArea = undefined;
    this.ageTree?.clear();
    this.updatePreview();
  }

  setupYearCard(): void {
    this.yearCard?.dialogOpened.subscribe(ok => {
      this.yearSelection.clear();
      this.prognosisYears.forEach(year => this.yearSelection.select(year));
    })
    this.yearCard?.dialogConfirmed.subscribe((ok)=>{
      this.yearCard?.setLoading(true);
      const progYears = this.yearSelection.selected;
      this.http.post<Year[]>(`${this.rest.URLS.years}set_prognosis_years/`, { years: progYears }
      ).subscribe(years => {
        this.years.forEach(y => y.isPrognosis = false);
        this.prognosisYears = [];
        years.forEach(ry => {
          if (ry.isPrognosis) this.prognosisYears.push(ry.year);
          const year = this.years.find(y => y.id === ry.id);
          if (year)
            Object.assign(year, ry);
        })
        this.prognosisYears.sort();
        this.previewYear = undefined;
        this.dataYear = undefined;
        this.ageTree?.clear();
        this.updatePreview();
        this.yearCard?.closeDialog(true);
      });
    })
  }

  updatePreview(): void {
    if (this.previewLayer) {
      this.layerGroup?.removeLayer(this.previewLayer);
      this.previewLayer = undefined;
    }
    if (!this.activePrognosis || !this.previewYear) return;
    const population = this.populations.find(p => p.year === this.previewYear!.id && p.prognosis === this.activePrognosis!.id);
    if (!population) return;
    this.popService.getPopEntries(population.id).subscribe(popEntries => {
      this.popEntries = {};
      popEntries.forEach(pe => {
        if (!this.popEntries[pe.area]) this.popEntries[pe.area] = [];
        this.popEntries[pe.area].push(pe);
      })
      let max = 1000;
      this.dataRows = [];
      this.areas.forEach(area => {
        const entries = this.popEntries[area.id];
        // map data
        const value = entries? entries.reduce((p: number, e: PopEntry) => p + e.value, 0): 0;
        area.properties.value = value;
        area.properties.description = `<b>${area.properties.label}</b><br>Bevölkerung: ${area.properties.value}`
        max = Math.max(max, value);
      })
      this.previewLayer = this.layerGroup?.addVectorLayer(this.popLevel!.name, {
        order: 0,
        description: this.popLevel!.name,
        style: {
          strokeColor: 'white',
          fillColor: 'rgba(165, 15, 21, 0.9)',
          symbol: 'circle'
        },
        labelField: 'value',
        tooltipField: 'description',
        mouseOver: {
          enabled: true,
          style: {
            strokeColor: 'yellow',
            fillColor: 'rgba(255, 255, 0, 0.7)'
          }
        },
        select: {
          enabled: true,
          style: {
            strokeColor: 'rgb(180, 180, 0)',
            fillColor: 'rgba(255, 255, 0, 0.9)'
          }
        },
        valueStyles: {
          field: 'value',
          radius: {
            range: [5, 50],
            scale: 'sqrt'
          },
          min: 0,
          max: max
        }
      });
      this.previewLayer?.addFeatures(this.areas, {
        properties: 'properties',
        geometry: 'centroid',
        zIndex: 'value'
      });
      if (this.previewArea)
        this.previewLayer?.selectFeatures([this.previewArea.id], { silent: true });
      this.updateAgeTree();
      this.previewLayer?.featuresSelected.subscribe(features => {
        this.previewArea = this.areas.find(area => area.id === features[0].get('id'));
        this.updateAgeTree();
      })
      this.previewLayer?.featuresDeselected.subscribe(features => {
        if (this.previewArea?.id === features[0].get('id')) {
          this.previewArea = undefined;
          this.updateAgeTree();
        }
      })
    })
  }

  deleteData(year: Year): void {
    if (!year.hasPrognosisData) return;
    const dialogRef = this.dialog.open(RemoveDialogComponent, {
      width: '400px',
      data: {
        title: 'Entfernung von Prognosedaten',
        message: 'Sollen die Prognosedaten dieses Jahres wirklich entfernt werden?',
        confirmButtonText: 'Prognosedaten entfernen',
        value: year.year
      }
    });
    dialogRef.afterClosed().subscribe((confirmed: boolean) => {
      const population = this.populations.find(p => p.year === year.id);
      if (!population) return;
      if (confirmed) {
        this.http.delete(`${this.rest.URLS.populations}${population.id}/?force=true`
        ).subscribe(res => {
          const idx = this.populations.indexOf(population);
          if (idx > -1) this.populations.splice(idx, 1);
          year.hasPrognosisData = false;
          if (year === this.previewYear) {
            this.previewYear = undefined;
            this.ageTree?.clear();
            this.dataRows = [];
            this.updatePreview();
          }
        },(error) => {
          showAPIError(error, this.dialog);
        });
      }
    });
  }

  onAreaChange(): void {
    if (!this.previewLayer) return;
    this.previewLayer?.selectFeatures([this.previewArea!.id], { silent: true, clear: true });
    this.updateAgeTree();
  }

  updateAgeTree(): void {
    this.ageTree?.clear();
    if (!this.previewArea || !this.previewYear) return;
    const areaData = this.popEntries[this.previewArea.id];
    const maleId = this.genders.find(g => g.name === 'männlich')?.id || 1;
    const femaleId = this.genders.find(g => g.name === 'weiblich')?.id || 2;
    const ageTreeData: AgeTreeData[] = [];
    this.ageGroups.forEach(ageGroup => {
      const ad = areaData.filter(d => d.ageGroup === ageGroup.id);
      ageTreeData.push({
        male: ad.find(d => d.gender === maleId)?.value || 0,
        fromAge: ageGroup.fromAge,
        toAge: ageGroup.toAge,
        female: ad.find(d => d.gender === femaleId)?.value || 0,
        label: ageGroup.label || ''
      })
    })
    this.ageTree!.subtitle = `${this.previewArea?.properties.label!} ${this.previewYear?.year}`;
    this.ageTree!.draw(ageTreeData);
  }

  setupPropertiesCard(): void {
    this.propertiesCard?.dialogOpened.subscribe(ok => {
      this.propertiesForm.reset({
        name: this.activePrognosis?.name,
        description: this.activePrognosis?.description,
      });
    })
    this.propertiesCard?.dialogConfirmed.subscribe((ok)=>{
      this.propertiesForm.markAllAsTouched();
      if (this.propertiesForm.invalid) return;
      let attributes: any = {
        name: this.propertiesForm.value.name,
        description: this.propertiesForm.value.description
      }
      this.propertiesCard?.setLoading(true);
      this.http.patch<DemandRateSet>(`${this.rest.URLS.prognoses}${this.activePrognosis?.id}/`, attributes
      ).subscribe(prognosis => {
        Object.assign(this.activePrognosis!, prognosis);
        this.propertiesCard?.closeDialog(true);
      },(error) => {
        showAPIError(error, this.dialog);
        this.propertiesCard?.setLoading(false);
      });
    })
  }

  createPrognosis(): void {
    let dialogRef = this.dialog.open(ConfirmDialogComponent, {
      panelClass: 'absolute',
      width: '300px',
      disableClose: true,
      data: {
        title: 'Neue Prognosevariante',
        template: this.propertiesEdit,
        closeOnConfirm: false
      }
    });
    dialogRef.afterOpened().subscribe(ok => {
      this.propertiesForm.reset();
    });
    dialogRef.componentInstance.confirmed.subscribe(() => {
      // display errors for all fields even if not touched
      this.propertiesForm.markAllAsTouched();
      if (this.propertiesForm.invalid) return;
      let attributes: any = {
        name: this.propertiesForm.value.name,
        description: this.propertiesForm.value.description || ''
      }
      dialogRef.componentInstance.isLoading$.next(true);
      this.http.post<Prognosis>(this.rest.URLS.prognoses, attributes
      ).subscribe(prognosis => {
        this.prognoses.push(prognosis);
        this.activePrognosis = prognosis;
        this.onPrognosisChange();
        dialogRef.close();
      },(error) => {
        showAPIError(error, this.dialog);
        dialogRef.componentInstance.isLoading$.next(false);
      });
    });
  }

  deletePrognosis(): void {
    if (!this.activePrognosis)
      return;
    const dialogRef = this.dialog.open(RemoveDialogComponent, {
      width: '400px',
      data: {
        title: $localize`Die Prognosevariante wirklich entfernen?`,
        confirmButtonText: $localize`Variante entfernen`,
        message: 'Es werden auch alle bereits eingespielten Daten der Variante entfernt.',
        value: this.activePrognosis.name
      }
    });
    this.isLoading$.next(true);
    dialogRef.afterClosed().subscribe((confirmed: boolean) => {
      if (confirmed) {
        this.http.delete(`${this.rest.URLS.prognoses}${this.activePrognosis?.id}/?force=true`
        ).subscribe(() => {
          this.activePrognosis = undefined;
          this.isLoading$.next(false);
          // other prognosis might change on deletion of the default one
          this.popService.fetchPrognoses().subscribe(prognoses => this.prognoses = prognoses);
        },(error) => {
          showAPIError(error, this.dialog);
          this.isLoading$.next(false);
        });
      }
    });
  }

  showDataTable(): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      panelClass: 'absolute',
      width: '400',
      disableClose: false,
      autoFocus: false,
      data: {
        title: 'Datentabelle mit Prognosedaten der ausgewählten Variante: '+this.activePrognosis?.name,
        template: this.dataTemplate,
        hideConfirmButton: true,
        cancelButtonText: 'OK'
      }
    });
    dialogRef.afterOpened().subscribe(()=> this.updateTableData())
  }

  updateTableData(): void {
    this.dataRows = [];
    if (!this.dataYear) return;
    const population = this.populations.find(p => p.year === this.dataYear!.id && p.prognosis === this.activePrognosis!.id);
    if (!population) return;
    let rows: any[][] = [];
    this.isLoading$.next(true);
    this.popService.getPopEntries(population.id).subscribe(popEntries => {
      this.areas.forEach(area => {
        const entries = popEntries.filter(e => e.area === area.id);
        const row: any[] = [area.properties.label]
        if (!entries) return;
        // table data
        this.genders.forEach(gender => {
          const gEntries = entries.filter(e => e.gender === gender.id);
          this.ageGroups.forEach(ageGroup => {
            const entry = gEntries.find(e => e.ageGroup === ageGroup.id);
            row.push(entry?.value || 0);
          })
        })
        rows.push(row);
      })
      this.dataRows = rows;
      this.isLoading$.next(false);
    })
  }

  downloadTemplate(): void {
    if (!(this.popLevel && this.activePrognosis)) return;
    const url = `${this.rest.URLS.popEntries}create_template/`;
    const dialogRef = SimpleDialogComponent.show('Bereite Template vor. Bitte warten', this.dialog, { showAnimatedDots: true });
    this.http.post(url, { area_level: this.popLevel.id, years: this.prognosisYears, prognosis: this.activePrognosis.id }, { responseType: 'blob' }).subscribe((res:any) => {
      const blob: any = new Blob([res],{ type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      fileSaver.saveAs(blob, 'prognosedaten-'+ this.activePrognosis?.name+'.xlsx');
      dialogRef.close();
    },(error) => {
      showAPIError(error, this.dialog);
      dialogRef.close();
    });
  }

  uploadTemplate(): void {
    if (!this.activePrognosis) return;
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      panelClass: 'absolute',
      data: {
        title: `Befüllte Vorlage hochladen`,
        confirmButtonText: 'Datei hochladen',
        template: this.fileUploadTemplate,
        closeOnConfirm: false,
      }
    });
    dialogRef.componentInstance.confirmed.subscribe(() => {
      if (!this.file)
        return;
      const formData = new FormData();
      dialogRef.componentInstance.isLoading$.next(true);
      formData.append('excel_file', this.file);
      formData.append('prognosis', this.activePrognosis!.id.toString());
      const url = `${this.rest.URLS.popEntries}upload_template/`;
      this.http.post(url, formData).subscribe(res => {
        this.isProcessing$.next(true);
        dialogRef.close();
      }, error => {
        showAPIError(error, this.dialog);
        dialogRef.componentInstance.isLoading$.next(false);
      });
    });
  }

  setDefaultPrognosis(prognosis: Prognosis): void {
    if (!prognosis) return;
    const attributes = { isDefault: true };
    this.isLoading$.next(true);
    this.http.patch<Prognosis>(`${this.rest.URLS.prognoses}${this.activePrognosis?.id}/`, attributes
    ).subscribe(prognosis => {
      this.prognoses.forEach(p => p.isDefault = false);
      this.activePrognosis!.isDefault = prognosis.isDefault;
      this.isLoading$.next(false);
    })
  }

  onMessage(log: LogEntry): void {
    if (log?.status?.finished) {
      this.isProcessing$.next(false);
      this.popService.reset();
      this.fetchData();
    }
  }

  setFiles(event: Event){
    const element = event.currentTarget as HTMLInputElement;
    const files: FileList | null = element.files;
    this.file =  (files && files.length > 0)? files[0]: undefined;
  }

  ngOnDestroy(): void {
    this.mapControl?.destroy();
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
