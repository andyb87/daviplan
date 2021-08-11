import { AfterViewInit, Component, Input } from '@angular/core';
import * as d3 from 'd3';
import { StackedData } from "../stacked-barchart/stacked-barchart.component";

export interface MultilineData {
  group: string,
  values: number[]
}

@Component({
  selector: 'app-multiline-chart',
  templateUrl: './multiline-chart.component.html',
  styleUrls: ['./multiline-chart.component.scss']
})
export class MultilineChartComponent implements AfterViewInit {

  @Input() data?: MultilineData[];
  @Input() title: string = '';
  @Input() subtitle: string = '';
  @Input() labels?: string[];
  @Input() drawLegend: boolean = true;
  @Input() xLabel?: string;
  @Input() yLabel?: string;
  @Input() width?: number;
  @Input() height?: number;
  @Input() unit?: string;
  @Input() min?: number;
  @Input() max?: number;
  @Input() animate?: boolean;
  @Input() xSeparator?: { leftLabel?: string, rightLabel?:string, x: string, highlight?: boolean };

  private svg: any;
  private margin: {top: number, bottom: number, left: number, right: number } = {
    top: 50,
    bottom: 50,
    left: 60,
    right: 60
  };

  ngAfterViewInit(): void {
    this.createSvg();
    if (this.data) this.draw(this.data);
  }

  private createSvg(): void {
    let figure = d3.select("figure#multiline-chart");
    if (!(this.width && this.height)){
      let node: any = figure.node()
      let bbox = node.getBoundingClientRect();
      if (!this.width)
        this.width = bbox.width;
      if (!this.height)
        this.height = bbox.height;
    }
    this.svg = figure.append("svg")
      .attr("width", this.width!)
      .attr("height", this.height!)
      .append("g");
  }

  public draw(data: MultilineData[]): void {
    if (data.length == 0) return

    if (!this.labels)
      this.labels = d3.range(0, data[0].values.length).map(d=>d.toString());
    let colorScale = d3.scaleOrdinal(d3.schemeCategory10);
    let innerWidth = this.width! - this.margin.left - this.margin.right,
      innerHeight = this.height! - this.margin.top - this.margin.bottom;
    let groups = data.map(d => d.group);
    // Add X axis
    const x = d3.scaleBand()
      .range([0, innerWidth])
      .domain(groups)
      .padding(0);

    // x axis
    this.svg.append("g")
      .attr("transform",`translate(${this.margin.left},${innerHeight + this.margin.top})`)
      .call(d3.axisBottom(x))
      .selectAll("text")
      .attr("transform", "translate(-10,0)rotate(-45)")
      .style("text-anchor", "end");

    let max = this.max || d3.max(data, d => { return d3.max(d.values) });
    // y axis
    const y = d3.scaleLinear()
      .domain([this.min || 0, max!])
      .range([innerHeight, 0]);

    this.svg.append("g")
      .attr("transform", `translate(${this.margin.left},${this.margin.top})`)
      .call(
        d3.axisLeft(y)
          .tickFormat((y: any) => (this.unit) ? `${y}${this.unit}` : y)
      );

    if (this.yLabel)
      this.svg.append('text')
        .attr("y", 10)
        .attr("x", -(this.margin.top + 30))
        .attr('dy', '0.5em')
        .style('text-anchor', 'end')
        .attr('transform', 'rotate(-90)')
        .attr('font-size', '0.8em')
        .text(this.yLabel);

    if (this.xLabel)
      this.svg.append('text')
        .attr("y", this.height! - 10)
        .attr("x", this.width! - this.margin.right)
        .attr('dy', '0.5em')
        .style('text-anchor', 'end')
        .attr('font-size', '0.8em')
        .text(this.xLabel);

    let line = d3.line()
      // .curve(d3.curveCardinal)
      .x((d: any) => x(d.group)!)
      .y((d: any) => y(d.value));

    let _this = this;

    let tooltip = d3.select('body')
      .append('div')
      .attr('class', 'tooltip')
      .style("display", 'none');

    let lineG = this.svg.append('g')
      .attr("transform", `translate(${this.margin.left + x.bandwidth()/2}, ${this.margin.top})`)
      .on("mouseover", () => {
        lineG.selectAll('circle').style("display", null);
        tooltip.style("display", null);
      })
      .on("mouseout", () => {
        lineG.selectAll('circle').style("display", 'none');
        tooltip.style("display", 'none');
      })
      .on("mousemove", onMouseMove);

    // helper rect to enlarge g for catching mouse moves
    lineG.append('rect')
      .attr("height", innerHeight)
      .attr("width", innerWidth)
      .attr("opacity", '0')

    function onMouseMove(this: any, event: MouseEvent){
      let xPos = d3.pointer(event)[0],
          xIdx = Math.floor((xPos + x.bandwidth()/2) / x.bandwidth()),
          groupData = data![xIdx];
      if (!groupData) return;
      lineG.selectAll('circle')
        .transition()
        .duration(this.animate ? 80 : 0)
        .attr("transform", (d: null, i: number) => `translate(${x(groups[xIdx])}, ${y(groupData.values[i])})`);
      let text = groupData.group + '<br>';
      _this.labels?.forEach((label, i)=>{
        text += `<b style="color: ${colorScale(i.toString())}">${label}</b>: ${groupData.values[i].toString().replace('.', ',')}${(_this.unit) ? _this.unit : ''}<br>`;
      })
      tooltip.html(text);
      tooltip.style('left', event.pageX + 15 + 'px')
        .style('top', event.pageY + 10 + 'px');
    }

    this.labels.forEach((label, i)=>{

      let di = data.map(d => {
        return {
          group: d.group,
          value: d.values[i]
        }
      });
      let path = lineG.append("path")
        .datum(di)
        .attr("class", "line")
        .attr("fill", "none")
        .attr("stroke", colorScale(i.toString()))
        .attr("stroke-width", 1.5)
        .attr("d", line);

      if (this.animate) {
        let length = path.node().getTotalLength();
        path.attr("stroke-dasharray", length + " " + length)
          .attr("stroke-dashoffset", length)
          .transition()
          .duration(1000)
          // .ease(d3.easeQuadOut)
          .attr("stroke-dashoffset", 0);
      }

      lineG.append("circle")
        .attr("r", 3)
        .attr("fill", colorScale(i.toString()))
        .attr("transform", `translate(${x(groups[0])}, ${y(data[0].values[i])})`)
        .style("display", 'none');
    })

    if (this.drawLegend) {
      let size = 15;

      this.svg.selectAll("legendRect")
        .data(this.labels.reverse())
        .enter()
        .append("rect")
        .attr("x", innerWidth + this.margin.left)
        .attr("y", (d: string, i: number) => 105 + (i * (size + 5))) // 100 is where the first dot appears. 25 is the distance between dots
        .attr("width", size)
        .attr("height", 3)
        .style("fill", (d: string, i: number) => colorScale(i.toString()));

      this.svg.selectAll("legendLabels")
        .data(this.labels.reverse())
        .enter()
        .append("text")
        .attr('font-size', '0.7em')
        .attr("x", innerWidth + this.margin.left + size * 1.2)
        .attr("y", (d: string, i: number) => 100 + (i * (size + 5) + (size / 2)))
        .style("fill", (d: string, i: number) => colorScale(i.toString()))
        .text((d: string) => d)
        .attr("text-anchor", "left")
        .style("alignment-baseline", "middle")
    }

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

    if (this.xSeparator) {
      let xSepPos = x(this.xSeparator.x)! + this.margin.left + x.bandwidth();
      this.svg.append('line')
        .style('stroke', 'black')
        .attr('x1', xSepPos)
        .attr('y1', this.margin.top)
        .attr('x2', xSepPos)
        .attr('y2', this.height)
        .attr('class', 'separator');
      if (this.xSeparator.leftLabel)
        this.svg.append('text')
          .attr("y", this.height! - 10)
          .attr("x", xSepPos - 5)
          .attr('dy', '0.5em')
          .style('text-anchor', 'end')
          .attr('font-size', '0.7em')
          .text(this.xSeparator.leftLabel);
      if (this.xSeparator.rightLabel)
        this.svg.append('text')
          .attr("y", this.height! - 10)
          .attr("x", xSepPos + 5)
          .attr('dy', '0.5em')
          .style('text-anchor', 'start')
          .attr('font-size', '0.7em')
          .text(this.xSeparator.rightLabel);
      if (this.xSeparator.highlight) {
        this.svg.append('rect')
          .attr("x", xSepPos)
          .attr("y", this.margin.top - 10) // 100 is where the first dot appears. 25 is the distance between dots
          .attr("width", innerWidth - x(this.xSeparator.x)! - x.bandwidth())
          .attr("height", innerHeight + 10)
          .attr("fill", 'white')
          .attr("opacity", 0.5)
          .attr('pointer-events', 'none')
      }
    }
  }
}
