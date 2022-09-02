import { AfterViewInit, Component, OnDestroy, TemplateRef, ViewChild } from '@angular/core';
import { MatDialog } from "@angular/material/dialog";
import { CookieService } from "../../../helpers/cookies.service";
import { PlanningService } from "../planning.service";
import { environment } from "../../../../environments/environment";
import {
  Capacity,
  Infrastructure,
  Place,
  PlanningProcess,
  RasterCell,
  Scenario,
  Service,
  TransportMode
} from "../../../rest-interfaces";
import { MapControl, MapService } from "../../../map/map.service";
import { Subscription } from "rxjs";
import { Geometry } from "ol/geom";
import {  MapLayerGroup, VectorLayer, VectorTileLayer } from "../../../map/layers";
import { modes } from "../mode-select/mode-select.component";

const modeColorValues = [[0,104,55],[100,188,97],[215,238,142],[254,221,141],[241,110,67],[165,0,38],[0,0,0]];
const modeColors = modeColorValues.map(c => `rgb(${c.join(',')})`);
const modeBins: Record<number, number[]> = {};
modeBins[TransportMode.WALK] = modeBins[TransportMode.BIKE] = [5, 10, 15, 20, 30, 45];
modeBins[TransportMode.CAR] = [5, 10, 15, 20, 25, 30];
modeBins[TransportMode.TRANSIT] = [10, 15, 20, 30, 45, 60];

@Component({
  selector: 'app-reachabilities',
  templateUrl: './reachabilities.component.html',
  styleUrls: ['./reachabilities.component.scss']
})
export class ReachabilitiesComponent implements AfterViewInit, OnDestroy {
  @ViewChild('filterTemplate') filterTemplate!: TemplateRef<any>;
  rasterCells: RasterCell[] = [];
  activeMode: TransportMode = TransportMode.WALK;
  indicator: 'place' | 'cell' | 'next' = 'place';
  infrastructures: Infrastructure[] = [];
  places: Place[] = [];
  activeInfrastructure?: Infrastructure;
  activeService?: Service;
  activeScenario?: Scenario;
  mapControl?: MapControl;
  placesLayerGroup?: MapLayerGroup;
  reachLayerGroup?: MapLayerGroup;
  baseRasterLayer?: VectorTileLayer;
  reachRasterLayer?: VectorTileLayer;
  private subscriptions: Subscription[] = [];
  private mapClickSub?: Subscription;
  placesLayer?: VectorLayer;
  year?: number;
  placeReachabilityLayer?: VectorLayer;
  nextPlaceReachabilityLayer?: VectorTileLayer;
  selectedPlaceId?: number;
  pickedCoords?: number[];

  constructor(private mapService: MapService, private dialog: MatDialog, public cookies: CookieService,
              public planningService: PlanningService) { }

  ngAfterViewInit(): void {
    this.mapControl = this.mapService.get('planning-map');
    this.placesLayerGroup = new MapLayerGroup('Standorte', { order: -1 })
    this.reachLayerGroup = new MapLayerGroup('Erreichbarkeiten', { order: -2 })
    this.mapControl.addGroup(this.placesLayerGroup);
    this.mapControl.addGroup(this.reachLayerGroup);
    this.applyUserSettings();
    this.planningService.getInfrastructures().subscribe(infrastructures => {
      this.infrastructures = infrastructures;
      // this.drawRaster();
/*      this.planningService.getRasterCells({targetProjection: this.mapControl?.map?.mapProjection }).subscribe(rasterCells => {
        this.rasterCells = rasterCells;
      });*/
      this.updatePlaces();
    });
    this.subscriptions.push(this.planningService.activeInfrastructure$.subscribe(infrastructure => {
      this.activeInfrastructure = infrastructure;
      this.updatePlaces();
      this.onIndicatorChange();
    }))
    this.subscriptions.push(this.planningService.activeService$.subscribe(service => {
      this.activeService = service;
      this.updatePlaces();
      this.onIndicatorChange();
    }))
    this.subscriptions.push(this.planningService.activeScenario$.subscribe(scenario => {
      this.activeScenario = scenario;
      this.updatePlaces();
      this.onIndicatorChange();
    }));
    this.subscriptions.push(this.planningService.year$.subscribe(year => {
      this.year = year;
      this.updatePlaces();
      // year is not relevant for the other indicators
      this.showNextPlaceReachabilities();
    }));
  }

  applyUserSettings(): void {
    this.activeMode = this.cookies.get('planning-mode', 'number') || TransportMode.WALK;
    // @ts-ignore
    this.indicator = this.cookies.get('planning-reach-indicator', 'string') || 'place';
  }

  drawRaster(): void {
    const url = `${environment.backend}/tiles/raster/{z}/{x}/{y}/`;
    this.baseRasterLayer = new VectorTileLayer( 'Rasterzellen', url,{
      order: 0,
      description: 'Zensus-Raster (LAEA)',
      opacity: 1,
      style: {
        fillColor: 'rgba(0, 0, 0, 0)',
        strokeWidth: 1,
        strokeColor: 'black',
        symbol: 'line'
      },
      labelField: 'label',
      showLabel: false
    });
    this.placesLayerGroup?.addLayer(this.baseRasterLayer);
    this.baseRasterLayer?.clearFeatures();
  }

  updatePlaces(): void {
    if (!this.activeInfrastructure || !this.activeService || !this.year) return;
    this.updateMapDescription();
    const scenario = this.activeScenario?.isBase? undefined: this.activeScenario
    this.planningService.getPlaces({
        targetProjection: this.mapControl!.map!.mapProjection, filter: { columnFilter: true, hasCapacity: true, year: this.year }, scenario: scenario
      }).subscribe(places => {
      this.places = places;
      let showLabel = true;
      if (this.placesLayer) {
        this.placesLayerGroup?.removeLayer(this.placesLayer);
        this.placesLayer = undefined;
      }
      this.placesLayer = new VectorLayer(this.activeInfrastructure!.name, {
        order: 1,
        zIndex: 99998,
        description: this.activeInfrastructure!.name,
        opacity: 1,
        radius: 7,
        style: {
          fillColor: '#2171b5',
          strokeColor: 'black',
          symbol: 'circle'
        },
        labelField: 'name',
        showLabel: showLabel,
        tooltipField: 'name',
        mouseOver: {
          enabled: true,
          // cursor: 'pointer'
          cursor: ''
        },
        select: {
          enabled: true,
          style: { fillColor: 'yellow' },
          multi: false
        },
        labelOffset: { y: 15 }
      });
      this.placesLayerGroup?.addLayer(this.placesLayer);
      this.placesLayer.addFeatures(places.map(place => {
        return { id: place.id, geometry: place.geom, properties: { name: place.name } }
      }));
      this.placesLayer?.setSelectable(this.indicator === 'place');

      this.placesLayer?.featureSelected?.subscribe(evt => {
        if (evt.selected) {
          this.selectedPlaceId = evt.feature.get('id');
          this.cookies.set('reachability-place', this.selectedPlaceId);
          this.showPlaceReachability();
        }
/*          else
          this.removePlaceReachability();*/
      })
/*        if (this.selectedPlaceId)
        this.placesLayer.selectFeatures([this.selectedPlaceId], { silent: false });*/
    })
  }

  onFilter(): void {
    this.updatePlaces();
    if (this.indicator === 'next')
      this.showNextPlaceReachabilities();
  }

  showPlaceReachability(): void {
    if (!this.rasterCells || this.selectedPlaceId === undefined) return;
    this.updateMapDescription('zur ausgewählten Einrichtung');
    this.planningService.getPlaceReachability(this.selectedPlaceId, this.activeMode, { scenario: this.activeScenario }).subscribe(cellResults => {
      let showLabel = this.reachRasterLayer?.showLabel;
      this.reachLayerGroup?.clear();
      let values: Record<string, number> = {};
      cellResults.forEach(cellResult => {
        values[cellResult.cellCode] = Math.round(cellResult.value);
      })

      const url = `${environment.backend}/tiles/raster/{z}/{x}/{y}/`;
      const place = this.places.find(p => p.id === this.selectedPlaceId);
      this.reachRasterLayer = new VectorTileLayer( `Wegezeit ${modes[this.activeMode]}`, url,{
        order: 0,
        description: `Erreichbarkeit des gewählten Standorts (${place?.name}) ${modes[this.activeMode]}`,
        opacity: 1,
        style: {
          fillColor: 'grey',
          strokeColor: 'rgba(0, 0, 0, 0)',
          symbol: 'line'
        },
        labelField: 'value',
        showLabel: showLabel,
        valueStyles: {
          fillColor: {
            bins: {
              colors: modeColors,
              values: modeBins[this.activeMode]
            }
          }
        },
        valueMap: {
          field: 'cellcode',
          values: values
        },
        unit: 'Minuten'
      });
      this.reachLayerGroup?.addLayer(this.reachRasterLayer);
    })
  }

  showCellReachability(): void {
    if (!this.rasterCells || this.pickedCoords === undefined) return;
    this.updateMapDescription('vom gewählten Wohnstandort zu allen Einrichtungen');
    const lat = this.pickedCoords[1];
    const lon = this.pickedCoords[0];
    this.planningService.getClosestCell(lat, lon, {targetProjection: this.mapControl?.map?.mapProjection }).subscribe(cell => {
      this.mapControl?.removeMarker();
      this.mapControl?.addMarker(cell.geom as Geometry);
      this.planningService.getCellReachability(cell.cellcode, this.activeMode, { scenario: this.activeScenario }).subscribe(placeResults => {
        let showLabel = this.placeReachabilityLayer?.showLabel;
        this.reachLayerGroup?.clear();
        this.places.forEach(place => {
          const res = placeResults.find(p => p.placeId === place.id);
          place.value = (res?.value !== undefined)? Math.round(res?.value): undefined;
        })
        this.placeReachabilityLayer = new VectorLayer(this.activeInfrastructure!.name, {
          order: 0,
          zIndex: 99999,
          description: this.activeInfrastructure!.name,
          opacity: 1,
          radius: 7,
          style: {
            fillColor: 'green',
            strokeColor: 'black',
            symbol: 'circle',
            strokeWidth: 1
          },
          labelField: 'label',
          showLabel: showLabel,
          tooltipField: 'label',
          valueStyles: {
            field: 'value',
            fillColor: {
              bins: {
                colors: modeColors,
                values: modeBins[this.activeMode]
              }
            }
          },
          unit: 'Minuten',
          labelOffset: { y: 10 }
        });
        this.reachLayerGroup?.addLayer(this.placeReachabilityLayer);
        this.placeReachabilityLayer.addFeatures(this.places.map(place => {
          return { id: place.id, geometry: place.geom, properties: {
            name: place.name, value: place.value,
            label: (place.value !== undefined)? `${place.value} Minuten`: 'nicht erreichbar' } }
        }));
      })
    });
  }

  showNextPlaceReachabilities(): void {
    if (!this.rasterCells || !this.year || !this.activeService) return;
    this.updateMapDescription('von allen Wohnstandorten zum jeweils nächsten Angebot');
    this.planningService.getNextPlaceReachability([this.activeService], this.activeMode, { scenario: this.activeScenario, year: this.year, places: this.places }).subscribe(cellResults => {
      let showLabel = this.nextPlaceReachabilityLayer?.showLabel;
      this.reachLayerGroup?.clear();
      let values: Record<string, number> = {};
      cellResults.forEach(cellResult => {
        values[cellResult.cellCode] = Math.round(cellResult.value);
      })
      const url = `${environment.backend}/tiles/raster/{z}/{x}/{y}/`;
      this.nextPlaceReachabilityLayer = new VectorTileLayer( `Wegezeit ${modes[this.activeMode]}`, url,{
        order: 0,
        description: 'Wegezeit von allen Wohnstandorten zum jeweils nächsten Angebot',
        opacity: 1,
        style: {
          fillColor: 'grey',
          strokeColor: 'rgba(0, 0, 0, 0)',
          symbol: 'line'
        },
        labelField: 'value',
        showLabel: showLabel,
        valueStyles: {
          fillColor: {
            bins: {
              colors: modeColors,
              values: modeBins[this.activeMode]
            }
          }
        },
        valueMap: {
          field: 'cellcode',
          values: values
        },
        unit: 'Minuten'
      });
      this.reachLayerGroup?.addLayer(this.nextPlaceReachabilityLayer);
    });
  }

  onIndicatorChange(): void {
    this.cookies.set('planning-reach-indicator', this.indicator);
    const placeSelectMode = this.indicator === 'place';
    const cellSelectMode = this.indicator === 'cell';
    this.setPlaceSelection(placeSelectMode);
    this.setMarkerPlacement(cellSelectMode);
    this.mapControl?.setCursor(placeSelectMode? 'search': cellSelectMode? 'marker': 'pointer');
    // this.mapControl?.setCursor(cellSelectMode? 'marker': 'default');
    this.mapControl?.removeMarker();
    if (this.placesLayer)
      this.placesLayer?.clearSelection();
    this.reachLayerGroup?.clear();
    this.updateMapDescription();
    if (this.indicator === 'next')
      this.showNextPlaceReachabilities();
  }

  setPlaceSelection(enable: boolean): void {
    this.placesLayer?.setSelectable(enable);
  }

  setMarkerPlacement(enable: boolean): void {
    if (this.mapClickSub) {
      this.mapClickSub.unsubscribe();
      this.mapClickSub = undefined;
    }
    if (enable) {
      this.mapClickSub = this.mapControl?.map?.mapClicked.subscribe(coords => {
        this.pickedCoords = coords;
        this.showCellReachability();
      })
    }
  }

  changeMode(mode: TransportMode): void {
    this.activeMode = mode;
    this.cookies.set('planning-mode', mode);
    switch (this.indicator) {
      case 'place':
        this.showPlaceReachability();
        break;
      case 'cell':
        this.showCellReachability();
        break;
      case 'next':
        this.showNextPlaceReachabilities();
        break;
      default:
        break;
    }
  }

  updateMapDescription(indicatorDesc?: string): void {
    let desc = `${this.activeScenario?.name}<br>
                  Erreichbarkeit "${this.activeService?.name}"<br>`;
    if (indicatorDesc) desc += `<b>Wegzeit ${(this.activeMode !== TransportMode.WALK)? 'mit dem ': ''}${modes[this.activeMode]} ${indicatorDesc}</b>`
    this.mapControl?.setDescription(desc);
  }

  ngOnDestroy(): void {
    this.mapClickSub?.unsubscribe();
    if (this.reachLayerGroup) this.mapControl?.removeGroup(this.reachLayerGroup);
    if (this.placesLayerGroup) this.mapControl?.removeGroup(this.placesLayerGroup);
    this.mapControl?.setCursor();
    this.mapControl?.removeMarker();
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
