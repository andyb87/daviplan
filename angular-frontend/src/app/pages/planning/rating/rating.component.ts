import { AfterViewInit, Component, OnDestroy, TemplateRef, ViewChild } from '@angular/core';
import { CookieService } from "../../../helpers/cookies.service";
import { environment } from "../../../../environments/environment";
import { MatDialog } from "@angular/material/dialog";
import { SimpleDialogComponent } from "../../../dialogs/simple-dialog/simple-dialog.component";
import { PlanningService } from "../planning.service";
import {
  Area,
  AreaIndicatorResult,
  AreaLevel,
  Indicator,
  Infrastructure,
  PlanningProcess,
  Service,
  TransportMode
} from "../../../rest-interfaces";
import { MapControl, MapService } from "../../../map/map.service";
import * as d3 from "d3";
import { Subscription } from "rxjs";
import { MapLayerGroup, VectorLayer } from "../../../map/layers";

@Component({
  selector: 'app-rating',
  templateUrl: './rating.component.html',
  styleUrls: ['./rating.component.scss']
})
export class RatingComponent implements AfterViewInit, OnDestroy {
  @ViewChild('diagramDialog') diagramDialogTemplate!: TemplateRef<any>;
  backend: string = environment.backend;
  years = [2009, 2010, 2012, 2013, 2015, 2017, 2020, 2025];
  compareSupply = true;
  compareStatus = 'option 1';
  indicators: Indicator[] = [];
  areaLevels: AreaLevel[] = [];
  areas: Area[] = [];
  infrastructures: Infrastructure[] = [];
  activeService?: Service;
  selectedIndicator?: Indicator;
  selectedAreaLevel?: AreaLevel;
  activeInfrastructure?: Infrastructure;
  activeProcess?: PlanningProcess;
  activeMode: TransportMode = TransportMode.WALK;
  mapControl?: MapControl;
  indicatorLayer?: VectorLayer;
  layerGroup?: MapLayerGroup;
  year?: number;
  subscriptions: Subscription[] = [];

  constructor(private dialog: MatDialog, public cookies: CookieService,
              public planningService: PlanningService, private mapService: MapService) {}

  ngAfterViewInit(): void {
    this.mapControl = this.mapService.get('planning-map');
    this.layerGroup = new MapLayerGroup('Bewertung', { order: -1 })
    this.mapControl.addGroup(this.layerGroup);
    this.planningService.getAreaLevels({ active: true }).subscribe(areaLevels => {
      this.areaLevels = areaLevels;
      this.planningService.getInfrastructures().subscribe(infrastructures => {
        this.infrastructures = infrastructures;
        this.subscriptions.push(this.planningService.year$.subscribe(year => {
          this.year = year;
          this.updateMap();
        }));
        this.subscriptions.push(this.planningService.activeInfrastructure$.subscribe(infrastructure => {
          this.activeInfrastructure = infrastructure;
        }))
        this.subscriptions.push(this.planningService.activeService$.subscribe(service => {
          this.activeService = service;
          this.onServiceChange();
        }));
/*        this.subscriptions.push(this.planningService.activeProcess$.subscribe(process => {
          this.activeProcess = process;
          this.onServiceChange();
        }));*/
        this.applyUserSettings();
      });
    })
  }

  applyUserSettings(): void {
    this.selectedAreaLevel = this.areaLevels.find(al => al.id === this.cookies.get('planning-area-level', 'number')) || ((this.areaLevels.length > 0)? this.areaLevels[this.areaLevels.length - 1]: undefined);
    this.onServiceChange();
    this.onAreaLevelChange();
  }

  onAreaLevelChange(): void {
    if(!this.selectedAreaLevel) return;
    this.planningService.getAreas(this.selectedAreaLevel!.id).subscribe(areas => {
      this.areas = areas;
      this.cookies.set('planning-area-level', this.selectedAreaLevel?.id);
      this.updateMap();
    })
  }

  onServiceChange(): void {
    if (!this.activeService) {
      this.indicators = [];
      this.selectedIndicator = undefined;
      return;
    }
    this.planningService.getIndicators(this.activeService.id).subscribe(indicators => {
      this.indicators = indicators;
      this.selectedIndicator = indicators?.find(i => i.name === this.cookies.get('planning-indicator', 'string'));
      this.updateMap();
    })
  }

  updateMap(): void {
    if (this.indicatorLayer) {
      this.layerGroup?.removeLayer(this.indicatorLayer);
      this.indicatorLayer = undefined;
    }
    this.updateMapDescription();
    switch (this.selectedIndicator?.resultType) {
      case 'area':
        this.renderAreaIndicator();
        break;
      case 'place':
        this.renderPlaceIndicator();
        break;
      default:
    }
  }

  renderPlaceIndicator(): void {
    if (!this.year || !this.selectedIndicator || !this.activeService) return;
    const scenarioId = this.planningService.activeScenario?.isBase ? undefined : this.planningService.activeScenario?.id;
    this.planningService.getPlaces().subscribe(places => {
      this.planningService.computeIndicator<AreaIndicatorResult>(this.selectedIndicator!.name, this.activeService!.id,
        { year: this.year!, scenario: scenarioId, mode: this.activeMode }).subscribe(results => {
        // ToDo description with filter
        this.indicatorLayer = new VectorLayer(this.activeInfrastructure!.name, {
          order: 0,
          // description: desc,
          opacity: 1,
          style: {
            fillColor: '#2171b5',
            strokeWidth: 2,
            strokeColor: 'black',
            symbol: 'circle'
          },
          labelField: 'label',
          showLabel: false,
          tooltipField: 'name',
          select: {
            enabled: true,
            style: {
              strokeWidth: 2,
              fillColor: 'yellow',
            },
            multi: false
          },
          mouseOver: {
            enabled: true,
            cursor: 'pointer'
          },
          valueStyles: {
            radius: {
              range: [5, 20],
              scale: 'linear'
            },
            strokeColor: {
              colorFunc: (feat => (feat.get('scenario') !== null) ? '#fc450c' : '#174a79')
            },
            field: 'capacity',
            min: this.activeService?.minCapacity || 0,
            max: this.activeService?.maxCapacity || 1000
          },
          labelOffset: { y: 15 }
        });
        this.layerGroup?.addLayer(this.indicatorLayer);
        this.indicatorLayer.addFeatures(places.map(place => {
          return {
            id: place.id,
            geometry: place.geom,
            properties: { name: place.name, label: place.label, capacity: place.capacity, scenario: place.scenario }
          }
        }));
      });
    });
  }

  renderAreaIndicator(): void {
    if (!this.year || !this.selectedAreaLevel || !this.selectedIndicator || !this.activeService || this.areas.length === 0) return;
    const scenarioId = this.planningService.activeScenario?.isBase ? undefined : this.planningService.activeScenario?.id;
    this.planningService.computeIndicator<AreaIndicatorResult>(this.selectedIndicator.name, this.activeService.id,
      { year: this.year!, scenario: scenarioId, areaLevelId: this.selectedAreaLevel.id, mode: this.activeMode }).subscribe(results => {
      let max = 0;
      let min = Number.MAX_VALUE;
      this.areas.forEach(area => {
        const data = results.find(d => d.areaId == area.id);
        const value = (data && data.value)? data.value: 0;
        max = Math.max(max, value);
        min = Math.min(min, value);
        area.properties.value = value;
        area.properties.description = `<b>${area.properties.label}</b><br>${this.selectedIndicator!.title}: ${area.properties.value}`
      })
      this.indicatorLayer = new VectorLayer(`${this.selectedIndicator!.title} (${this.selectedAreaLevel!.name})`, {
        order: 0,
        description: this.selectedIndicator!.description,
        opacity: 1,
        style: {
          strokeColor: 'white',
          fillColor: 'rgba(165, 15, 21, 0.9)',
          symbol: 'line'
        },
        labelField: 'value',
        showLabel: true,
        tooltipField: 'description',
        mouseOver: {
          enabled: true,
          style: {
            strokeColor: 'yellow',
            fillColor: 'rgba(255, 255, 0, 0.7)'
          }
        },
        valueStyles: {
          field: 'value',
          fillColor: {
            interpolation: {
              range: d3.interpolatePurples,
              scale: 'sequential',
              steps: 5
            }
          },
          min: min,
          max: max || 1
        },
      });
      this.layerGroup?.addLayer(this.indicatorLayer);
      this.indicatorLayer.addFeatures(this.areas,{ properties: 'properties' });
    })
  }

  updateMapDescription(): void {

  }

  onIndicatorChange(): void {
    this.cookies.set('planning-indicator', this.selectedIndicator?.name);
    this.updateMap();
  }

  changeMode(mode: TransportMode): void {
    this.activeMode = mode;
    this.updateMap();
  }

  onFullscreenDialog(): void {
    this.dialog.open(SimpleDialogComponent, {
      autoFocus: false,
      data: {
        template: this.diagramDialogTemplate
      }
    });
  }

  ngOnDestroy(): void {
    if (this.layerGroup) {
      this.mapControl?.removeGroup(this.layerGroup);
    }
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
