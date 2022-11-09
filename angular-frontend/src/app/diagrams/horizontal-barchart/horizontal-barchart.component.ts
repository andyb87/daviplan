import { AfterViewInit, Component, Input } from '@angular/core';
import * as d3 from 'd3';
import { DiagramComponent } from "../diagram/diagram.component";

export interface BarChartData {
  label: string,
  value: number,
  color?: string
}

@Component({
  selector: 'app-horizontal-barchart',
  templateUrl: '../diagram/diagram.component.html',
  styleUrls: ['./horizontal-barchart.component.scss', '../diagram/diagram.component.scss']
})
export class HorizontalBarchartComponent extends DiagramComponent implements AfterViewInit {
  @Input() data?: BarChartData[];
  @Input() subtitle: string = '';
  @Input() xLabel?: string;
  @Input() yLabel?: string;
  @Input() animate?: boolean;
  @Input() unit: string = '';
  localeFormatter = d3.formatLocale({
    decimal: ',',
    thousands: '.',
    grouping: [3],
    currency: ['€', '']
  })
  svg: any;
  @Input()  margin: {top: number, bottom: number, left: number, right: number } = {
    top: 50,
    bottom: 20,
    left: 20,
    right: 40
  };

  ngAfterViewInit(): void {
    this.createSvg();
    if (this.data) this.draw(this.data);
  }

  draw(data: BarChartData[]): void {
    this.clear();
    if (data.length == 0) return;
    const _this = this;
    this.data = data;

    const barHeight = 20,
      barPadding = 5,
      max = d3.max(data, d => d.value) || 1;

    const height = (barHeight + barPadding) * data.length

    this.svg.attr('viewBox', `0 0 ${this.width!} ${height + this.margin.left + this.margin.right}`);

    const scale = d3.scaleLinear()
      .domain([0, max])
      .range([0, this.width! - (this.margin.left + this.margin.right)]);

    this.svg.append('g')
      .attr('class', 'axis x right')
      .attr('transform', `translate(${ this.margin.left }, ${ this.margin.top })`)
      .call(
        d3.axisBottom(scale)
          .ticks(5)
          .tickSize(height)
          .tickFormat(d3.format('d'))
      );

    // tooltips
    function onMouseOverBar(this: any, event: MouseEvent) {
      let bar = d3.select(this);
      bar.select('rect').classed('highlight', true);
      const data = this.__data__;
      const formatter = _this.localeFormatter.format(',.2f');
      let text = `<b>${data.label}</b><br>${formatter(data.value)} ${_this.unit}`;
      tooltip.style('display', null);
      tooltip.html(text);
    };

    function onMouseOutBar(this: any, event: MouseEvent) {
      bars.select('rect').classed('highlight', false);
      tooltip.style('display', 'none');
    }

    function onMouseMove(this: any, event: MouseEvent){
      tooltip.style('left', event.pageX + 20 + 'px')
        .style('top', event.pageY + 10 + 'px');
    }

    const bars = this.svg.append('g').selectAll('g')
      .data(data)
      .enter()
      .append('g');

    bars.attr('class', 'bar')
      .attr('cx',0)
      .attr('transform', (d: BarChartData, i: number) => `translate(${this.margin.left}, ${this.margin.top + i * (barHeight + barPadding) + barPadding})`)
      .on('mouseover', onMouseOverBar)
      .on('mouseout', onMouseOutBar)
      .on('mousemove', onMouseMove);

    bars.append('rect')
      // .attr('transform', 'translate('+labelWidth+', 0)')
      .style('fill', (d: BarChartData) => d.color || '#6daf56')
      .attr('height', barHeight)
      .attr('width', (d: BarChartData) => {
          if (this.animate) return 0;
          return scale(d.value);
        })

    bars.append('text')
      .attr('class', 'label')
      .attr('y', barHeight / 2)
      .attr('dy', '.35em') //vertical align middle
      .text((d: BarChartData) => d.label);

    if (this.animate) {
      bars.selectAll('rect').transition()
        .duration(800)
        .attr('width', (d: BarChartData) => scale(d.value));
    }

    let tooltip = d3.select('body')
      .append('div')
      .attr('class', 'd3-tooltip')
      .style('display', 'none');

    this.svg.append('text')
      .attr('class', 'title')
      .attr('x', this.margin.left)
      .attr('y', 15)
      .text(this.title);

    this.svg.append('text')
      .attr('class', 'subtitle')
      .attr('x', this.margin.left)
      .attr('y', 15)
      .attr('font-size', '0.8em')
      .attr('dy', '1em')
      .text(this.subtitle);
  }

  getCSVRows(): (string | number)[][] {
    let rows = [['Name', `${this.title} ${this.unit? '(' + this.unit + ')': ''}`]];
    rows = rows.concat(this.data?.map(d => [d.label, d.value.toLocaleString()]) || []);
    return rows;
  }
}
