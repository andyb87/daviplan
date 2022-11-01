import { EventEmitter } from "@angular/core";
import { IndicatorLegendClass, Symbol } from "../rest-interfaces";
import { OlMap } from "./map";
import { Feature } from "ol";
import { Layer as OlLayer } from "ol/layer";
import { v4 as uuid } from "uuid";
import { sortBy } from "../helpers/utils";
import * as d3 from "d3";

export interface LayerStyle extends Symbol {
  strokeWidth?: number
}

interface LegendEntry {
  color: string,
  label: string,
  strokeColor?: string
}

interface ColorLegend {
  entries: LegendEntry[],
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
  zIndex?: number,
  attribution?: string,
  opacity?: number,
  visible?: boolean,
  active?: boolean,
  legend?: ColorLegend
}

export abstract class MapLayer {
  name: string;
  url?: string;
  id?: number | string;
  mapId?: string;
  group?: MapLayerGroup;
  description?: string = '';
  order?: number = 1;
  zIndex?: number;
  attribution?: string;
  opacity?: number = 1;
  visible?: boolean = true;
  map?: OlMap;
  active?: boolean;
  legend?: ColorLegend;
  protected _legend?: ColorLegend;

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
    this.zIndex = options?.zIndex;
    this._legend = options?.legend;
    if (options?.group) options?.group.addLayer(this);
  }

  getZIndex(): number {
    if (this.zIndex) return this.zIndex;
    let zIndex = 90 - (this.order || 0);
    if (this.group?.order)
      zIndex += 10000 - (this.group.order * 100);
    return zIndex;
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

  zoomTo(): void {
    this.map?.zoomToExtent(this.mapId!);
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
        zIndex: this.getZIndex(),
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

export interface ColorBin {
  from?: number;
  to?: number;
  color: string;
}

export interface ValueStyle {
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
    interpolation?: {
      range: Interpolator | string[],
      scale?: 'linear' | 'sequential',
      steps?: number,
      reverse?: boolean,
    }
    bins?: IndicatorLegendClass[],
    colorFunc?: ((d: number) => string)
  },
  min?: number,
  max?: number
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
  valueStyles?: ValueStyle,
  labelOffset?: { x?: number, y?: number }
}

function findBin(arr: number[], value: number) {
  let newArray = arr.concat(value)
  newArray.sort((a, b) => a - b)
  return newArray.indexOf(value);
}

export class VectorLayer extends MapLayer {
  featuresSelected: EventEmitter<Feature<any>[]>
  featuresDeselected: EventEmitter<Feature<any>[]>
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
  labelOffset?: { x?: number, y?: number };

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
    this.featuresSelected = new EventEmitter<Feature<any>[]>();
    this.featuresDeselected = new EventEmitter<Feature<any>[]>();
    this.valueStyles = options?.valueStyles;
    this.radius = options?.radius;
    this.unit = options?.unit;
    this.labelOffset = options?.labelOffset;
  }

  protected initFunctions(): void {
    if (this.valueStyles?.fillColor?.interpolation) {
      const seqFunc: any = (this.valueStyles.fillColor.interpolation.scale === 'linear')? d3.scaleLinear : d3.scaleSequential;
      const max = !this.valueStyles.fillColor.interpolation.reverse? this.valueStyles.max: this.valueStyles.min;
      const min = !this.valueStyles.fillColor.interpolation.reverse? this.valueStyles.min: this.valueStyles.max;
      this.valueStyles.fillColor.colorFunc = seqFunc(this.valueStyles.fillColor.interpolation.range).domain([min, max]);
    }
    if (this.valueStyles?.radius?.range) {
      const seqFunc: any = (this.valueStyles.radius.scale === 'linear')? d3.scaleLinear : d3.scaleSequential;
      let max = this.valueStyles.max;
      let min = this.valueStyles.min;
      this.valueStyles.radius.radiusFunc = seqFunc().domain([min, max]).range(this.valueStyles.radius.range);
    }
    if (this.valueStyles?.fillColor?.bins) {
      const colors = this.valueStyles!.fillColor!.bins!.map(b => b.color);
      const values = this.valueStyles!.fillColor!.bins!.map(b => b.maxValue || 99999999999999);
      this.valueStyles.fillColor.colorFunc = (value: number) => {
        const idx = findBin(values, value);
        return colors[idx];
      }
    }
  }

  addToMap(map?: OlMap): OlLayer<any> | undefined {
    if (map === this.map) return;
    if (map) this.map = map;
    if (!this.map) return;
    this.mapId = uuid();
    this.initFunctions();
    this.initSelect();
    return this.map!.addVectorLayer(this.mapId, {
      zIndex: this.getZIndex(),
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
      showLabel: this.showLabel,
      labelOffset: this.labelOffset
    })
  }

  protected _getColorLegend(): ColorLegend | undefined {
    if (this._legend) return this._legend;
    if (!this.valueStyles?.fillColor?.colorFunc || !this.map) return;
    let legend: ColorLegend = {
      entries: [],
      elapsed: true
    }
    const colorFunc = this.valueStyles.fillColor.colorFunc;
    if (this.valueStyles.fillColor.bins){
      this.valueStyles.fillColor.bins.forEach(bin => {
        let label = (bin.minValue == undefined)? `bis ${bin.maxValue?.toLocaleString()}`:
            (bin.maxValue == undefined)? `ab ${bin.minValue.toLocaleString()}`:
              `${bin.minValue.toLocaleString()} bis ${bin.maxValue.toLocaleString()}`;
        if (this.unit)
          label += ` ${this.unit}`;
        legend.entries.push({
          label: label,
          color: bin.color
        });
      })
      return legend;
    }
    if (this.valueStyles.fillColor.interpolation) {
      const steps = (this.valueStyles.fillColor.interpolation.steps != undefined) ? this.valueStyles.fillColor.interpolation.steps : 5;
      let max = this.valueStyles.max;
      let min = this.valueStyles.min;
      if (max === undefined || min === undefined) {
        const features = this.map?.getLayer(this.mapId!).getSource().getFeatures();
        const values = features.map((f: Feature<any>) => f.get(this.valueStyles?.field!));
        if (max === undefined) max = Math.max(...values);
        if (min === undefined) min = Math.min(...values);
      }
      let step = (max - min) / steps;
      // if (this.valueStyles.extendLegendRange) step += 1;
      Array.from({ length: steps + 1 }, (v, k) => k * step).forEach((value, i) => {
        let label = Number(value.toFixed(2)).toLocaleString();
        if (this.unit)
          label += ` ${this.unit}`;
        legend.entries.push({
          label: label,
          color: colorFunc(value)
        })
      })
      return legend
    }
    return;
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
    this.legend = this._getColorLegend();
    return olFeatures;
  }

  protected initSelect() {
    this.map?.selected.subscribe(evt => {
      if (evt.layer.get('id') !== this.id) return;
      if (evt.selected && evt.selected.length > 0)
        this.featuresSelected.emit(evt.selected);
      if (evt.deselected && evt.deselected.length > 0)
        this.featuresDeselected.emit(evt.deselected);
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
    this.featuresSelected.unsubscribe();
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
    this.initFunctions();
    this.initSelect();
    if (this.valueStyles?.fillColor)
      this.legend = this._getColorLegend();
    return this.map.addVectorTileLayer(this.mapId, this.url!,{
      zIndex: this.getZIndex(),
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
