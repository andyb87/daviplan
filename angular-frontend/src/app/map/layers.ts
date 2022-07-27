import { EventEmitter } from "@angular/core";
import { Symbol } from "../rest-interfaces";
import { OlMap } from "./map";
import { Feature } from "ol";
import { Layer as OlLayer } from "ol/layer";
import { v4 as uuid } from "uuid";
import { sortBy } from "../helpers/utils";
import * as d3 from "d3";

export interface LayerStyle extends Symbol {
  strokeWidth?: number
}

interface ColorLegend {
  colors: string[],
  labels: string[],
  elapsed?: boolean
}

export class MapLayerGroup {
  name: string;
  id?: number | string;
  children: MapLayer[] = [];
  external?: boolean;
  map?: OlMap;
  order?: number;

  constructor(name: string, options?: {
    order?: number,
    external?: boolean,
    id?: number,
    global?: boolean
  }) {
    this.id = options?.id;
    this.name = name;
    this.external = options?.external;
    this.order = options?.order;
  }

  addLayer(layer: MapLayer): void {
    layer.group = this;
    // only add if not already a child
    if (this.children.indexOf(layer) < 0) {
      this.children.push(layer);
      this.children = sortBy(this.children, 'order');
      layer.addToMap(this.map);
    }
  }

  removeLayer(layer: MapLayer): void {
    const idx = this.children.indexOf(layer);
    if (idx < 0) return;
    this.children.splice(idx, 1);
    layer.removeFromMap();
  }

  clear(): void {
    this.children.forEach(l => l.removeFromMap());
    this.children = [];
  }
}

interface LayerOptions {
  id?: string | number,
  group?: MapLayerGroup,
  url?: string,
  description?: string,
  order?: number,
  attribution?: string,
  opacity?: number,
  visible?: boolean,
  active?: boolean
}

export abstract class MapLayer {
  name: string;
  url?: string;
  id?: number | string;
  mapId?: string;
  group?: MapLayerGroup;
  description?: string = '';
  order?: number = 1;
  attribution?: string;
  opacity?: number = 1;
  visible?: boolean = true;
  map?: OlMap;
  active?: boolean;
  colorLegend?: ColorLegend;

  protected constructor(name: string, options?: LayerOptions) {
    this.name = name;
    this.id = options?.id;
    this.map = options?.group?.map;
    this.url = options?.url;
    this.description = options?.description;
    this.attribution = options?.attribution;
    this.opacity = options?.opacity;
    this.visible = options?.visible;
    this.order = options?.order;
    this.active = options?.active;
    if (options?.group) options?.group.addLayer(this);
  }

  setOpacity(opacity: number) {
    this.opacity = opacity;
    this.map?.setOpacity(this.mapId!, opacity);
  }

  setVisible(visible: boolean) {
    this.visible = visible;
    this.map?.setVisible(this.mapId!, visible);
  }

  clearFeatures(): void {
    this.map?.clear(this.mapId!);
  }

  removeFromMap(): void {
    this.map?.removeLayer(this.mapId!);
    this.mapId = undefined;
    this.map = undefined;
  }

  abstract addToMap(map?: OlMap): OlLayer<any> | undefined;
}

interface TileLayerOptions extends LayerOptions {
  legendUrl?: string,
  layerName?: string
}

export class TileLayer extends MapLayer {
  protected xyz: boolean = true;
  layerName?: string;
  legendUrl?: string;

  constructor(name: string, url: string, options?: TileLayerOptions) {
    super(name, options);
    this.url = url;
    this.layerName = options?.layerName;
    this.legendUrl = options?.legendUrl;
  }

  addToMap(map?: OlMap): OlLayer<any> | undefined {
    if (map === this.map) return;
    if (map) this.map = map;
    if (!this.map) return;
    this.mapId = uuid();
    return this.map.addTileServer(
      this.mapId, this.url!, {
        params: { layers: this.layerName },
        visible: this.visible,
        opacity: this.opacity,
        xyz: this.xyz,
        attribution: this.attribution
      });
  }
}

export class WMSLayer extends TileLayer {
  protected xyz: boolean = false;

  addToMap(map?: OlMap): OlLayer<any> | undefined {
    const olLayer = super.addToMap(map);
    if (!olLayer) return;
    if (!this.legendUrl) {
      let url = olLayer.getSource().getLegendUrl(1, { layer: this.layerName });
      if (url) url += '&SLD_VERSION=1.1.0';
      this.legendUrl = url;
    }
    return olLayer;
  }
}

type Interpolator = ((d: number) => string);

interface ValueStyle {
  field?: string,
  radius?: {
    range: number[],
    scale?: 'linear' | 'sequential',
    radiusFunc?: ((d: number) => number)
  },
  strokeColor?: {
    colorFunc?: ((f: Feature<any>) => string)
  },
  fillColor?: {
    range?: Interpolator | string[],
    scale?: 'linear' | 'sequential',
    bins?: number,
    reverse?: boolean,
    colorFunc?: ((d: number) => string)
  },
  min?: number,
  max?: number,
  steps?: number
}

interface VectorLayerOptions extends LayerOptions {
  showLabel?: boolean,
  tooltipField?: string,
  labelField?: string,
  style?: LayerStyle,
  mouseOver?: {
    enabled: boolean,
    cursor?: string,
    style?: LayerStyle
  },
  select?: {
    enabled: boolean,
    multi?: boolean,
    style?: LayerStyle
  },
  radius?: number,
  unit?: string,
  valueStyles?: ValueStyle
}

export class VectorLayer extends MapLayer {
  featureSelected: EventEmitter<{ feature: any, selected: boolean }>
  showLabel?: boolean;
  tooltipField?: string;
  labelField?: string;
  selectable?: boolean;
  mouseOver?: boolean;
  mouseOverCursor?: string;
  multiSelect?: boolean;
  style?: LayerStyle;
  mouseOverStyle?: LayerStyle;
  selectStyle?: LayerStyle;
  attribution?: string;
  opacity?: number = 1;
  visible?: boolean = true;
  radius?: number;
  unit?: string;
  valueStyles?: ValueStyle;

  constructor(name: string, options?: VectorLayerOptions) {
    super(name, options);
    this.showLabel = options?.showLabel;
    this.tooltipField = options?.tooltipField;
    this.labelField = options?.labelField;
    this.style = options?.style;
    this.mouseOver = options?.mouseOver?.enabled;
    this.mouseOverStyle = options?.mouseOver?.style;
    this.selectable = options?.select?.enabled;
    this.selectStyle = options?.select?.style;
    this.selectable = options?.select?.enabled;
    this.multiSelect = options?.select?.multi;
    this.mouseOverCursor = options?.mouseOver?.cursor;
    this.featureSelected = new EventEmitter<any>();
    this.valueStyles = options?.valueStyles;
    this.radius = options?.radius;
    this.unit = options?.unit;
  }

  protected initColor(): void {
    if (!this.valueStyles?.fillColor?.colorFunc && this.valueStyles?.fillColor?.range) {
      const seqFunc: any = (this.valueStyles.fillColor.scale === 'linear')? d3.scaleLinear : d3.scaleSequential;
      const max = !this.valueStyles.fillColor.reverse? this.valueStyles.max: this.valueStyles.min;
      const min = !this.valueStyles.fillColor.reverse? this.valueStyles.min: this.valueStyles.max;
      this.valueStyles.fillColor.colorFunc = seqFunc(this.valueStyles.fillColor.range).domain([min, max]);
    }
    if (this.valueStyles?.radius?.range) {
      const seqFunc: any = (this.valueStyles.radius.scale === 'linear')? d3.scaleLinear : d3.scaleSequential;
      let max = this.valueStyles.max;
      let min = this.valueStyles.min;
      this.valueStyles.radius.radiusFunc = seqFunc().domain([min, max]).range(this.valueStyles.radius.range);
    }
  }

  addToMap(map?: OlMap): OlLayer<any> | undefined {
    if (map === this.map) return;
    if (map) this.map = map;
    if (!this.map) return;
    this.mapId = uuid();
    this.initColor();
    this.initSelect();
    return this.map!.addVectorLayer(this.mapId, {
      visible: this.visible,
      opacity: this.opacity,
      valueField: this.valueStyles?.field || 'value',
      mouseOverCursor: this.mouseOverCursor,
      multiSelect: this.multiSelect,
      stroke: {
        color: this.valueStyles?.strokeColor?.colorFunc || this.style?.strokeColor,
        width: this.style?.strokeWidth || 2,
        mouseOverColor: this.mouseOverStyle?.strokeColor,
        selectedColor: this.selectStyle?.strokeColor
      },
      fill: {
        color: this.valueStyles?.fillColor?.colorFunc || this.style?.fillColor,
        mouseOverColor: this.mouseOverStyle?.fillColor,
        selectedColor: this.selectStyle?.fillColor
      },
      radius: this.valueStyles?.radius?.radiusFunc || this.radius || 5,
      labelField: this.labelField,
      tooltipField: this.tooltipField,
      shape: (this.style?.symbol !== 'line')? this.style?.symbol: undefined,
      selectable: this.selectable,
      showLabel: this.showLabel
    })
  }

  protected _getColorLegend(): ColorLegend | undefined {
    if (!this.valueStyles?.fillColor?.colorFunc || !this.map) return;
    let colors: string[] = [];
    let labels: string[] = [];
    const steps = (this.valueStyles.steps != undefined)? this.valueStyles.steps: 5;
    let max = this.valueStyles.max;
    let min = this.valueStyles.min;
    if (max === undefined || min === undefined){
      const features = this.map?.getLayer(this.mapId!).getSource().getFeatures();
      const values = features.map((f: Feature<any>) => f.get(this.valueStyles?.field!));
      if (max === undefined) max = Math.max(...values);
      if (min === undefined) min = Math.min(...values);
    }
    const step = (max - min) / steps;
    const colorFunc = this.valueStyles.fillColor.colorFunc;
    Array.from({ length: steps + 1 },(v, k) => k * step).forEach((value, i) => {
      colors.push(colorFunc(value));
      let label = Number(value.toFixed(2)).toString();
      if (this.unit)
        label += ` ${this.unit}`;
      labels.push(label);
    })
    return {
      colors: colors,
      labels: labels,
      elapsed: true
    }
  }

  addFeatures(features: any[], options?: {
    properties?: string, geometry?: string, zIndex?: string
  }): Feature<any>[] | undefined {
    if (!this.map) return;
    let olFeatures: Feature<any>[] = [];
    const properties = (options?.properties !== undefined) ? options?.properties : 'properties';
    const geometry = (options?.geometry !== undefined) ? options?.geometry : 'geometry';
    features.forEach(feature => {
      if (!(feature instanceof Feature)) {
        const olFeature = new Feature(feature[geometry]);
        if (feature.id != undefined) {
          olFeature.set('id', feature.id);
          olFeature.setId(feature.id);
        }
        olFeature.setProperties(feature[properties]);
        olFeatures.push(olFeature);
      }
      else olFeatures.push(feature);
    })
    if (options?.zIndex) {
      const attr = options?.zIndex;
      olFeatures = olFeatures.sort((a, b) =>
        (a.get(attr) > b.get(attr)) ? 1 : (a.get(attr) < b.get(attr)) ? -1 : 0);
      olFeatures.forEach((feat, i) => feat.set('zIndex', olFeatures.length - i));
    }
    this.map.addFeatures(this.mapId!, olFeatures);
    if (this.valueStyles?.fillColor)
      this.colorLegend = this._getColorLegend();
    return olFeatures;
  }

  protected initSelect() {
    this.map?.selected.subscribe(evt => {
      if (evt.selected && evt.selected.length > 0)
        evt.selected.forEach(feature => this.featureSelected.emit({ feature: feature, selected: true }));
      if (evt.deselected && evt.deselected.length > 0)
        evt.deselected.forEach(feature => this.featureSelected.emit({ feature: feature, selected: false }));
    })
  }

  setSelectable(selectable: boolean): void {
    this.selectable = selectable;
    this.map?.setSelectActive(this.mapId!, selectable);
  }

  selectFeatures(ids: number[], options?: { silent?: boolean, clear?: boolean } ): void {
    if (!this.mapId) return;
    this.map?.selectFeatures(this.mapId, ids, options);
  }

  clearSelection(): void {
    if (!this.mapId) return;
    this.map?.deselectAllFeatures(this.mapId);
  }

  setShowLabel(show: boolean): void {
    this.showLabel = show;
    this.map?.setShowLabel(this.mapId!, show);
  }

  removeFeature(feature: Feature<any> | number): void {
    this.map?.removeFeature(this.mapId!, feature);
  }

  removeFromMap(): void {
    this.setSelectable(false);
    this.featureSelected.unsubscribe();
    this.map?.removeLayer(this.mapId!);
    this.mapId = undefined;
    this.map = undefined;
  }
}

interface ValueMap {
  field: string,
  values: Record<string, number>
}

interface VectorTileLayerOptions extends VectorLayerOptions {
  valueMap?: ValueMap
}

export class VectorTileLayer extends VectorLayer {
  valueMap?: ValueMap;

  constructor(name: string, url: string | undefined, options?: VectorTileLayerOptions) {
    super(name, options);
    this.url = url;
    this.valueMap = options?.valueMap;
  }

  addToMap(map?: OlMap): OlLayer<any> | undefined {
    if (map === this.map) return;
    if (map) this.map = map;
    if (!this.map) return;
    this.mapId = uuid();
    this.initColor();
    this.initSelect();
    if (this.valueStyles?.fillColor)
      this.colorLegend = this._getColorLegend();
    return this.map.addVectorTileLayer(this.mapId, this.url!,{
      visible: this.visible,
      opacity: this.opacity,
      stroke: {
        color: this.style?.strokeColor,
        width: this.style?.strokeWidth || 2,
        mouseOverColor: this.mouseOverStyle?.strokeColor
      },
      fill: {
        color: this.valueStyles?.fillColor?.colorFunc || this.style?.fillColor,
        mouseOverColor: this.mouseOverStyle?.fillColor
      },
      tooltipField: this.tooltipField,
      featureClass: this.mouseOver? 'feature': 'renderFeature',
      labelField: this.labelField,
      showLabel: this.showLabel,
      valueMap: this.valueMap
    });
  }
}
