import { AfterViewInit, Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { ModeStatistics, Scenario, TransportMode } from "../../../rest-interfaces";
import { PlanningService } from "../planning.service";
import { Subscription } from "rxjs";

export const modes: Record<number, string> = {};
modes[TransportMode.WALK] = 'zu Fuß';
modes[TransportMode.BIKE] = 'Fahrrad';
modes[TransportMode.CAR] = 'Auto';
modes[TransportMode.TRANSIT] = 'ÖPNV';

@Component({
  selector: 'app-mode-select',
  templateUrl: './mode-select.component.html',
  styleUrls: ['./mode-select.component.scss']
})
export class ModeSelectComponent implements OnDestroy{
  @Input() label?: string;
  @Output() modeChanged = new EventEmitter<TransportMode | undefined>();
  TransportMode = TransportMode;
  modes = modes;
  Number = Number;
  modeStatus: Record<number, { enabled: boolean, message: string }> = {};
  scenario?: Scenario;
  selectedMode?: TransportMode;
  private subscriptions: Subscription[] = [];

  @Input() set selected(mode: TransportMode | undefined) {
    this.selectedMode = mode;
  }

  constructor(private planningService: PlanningService) {
    this.subscriptions.push(this.planningService.activeScenario$.subscribe(scenario => {
      this.scenario = scenario;
      this.verifyModes();
    }));
  }

  changeMode(mode: TransportMode | undefined): void {
    this.selectedMode = mode;
    this.modeChanged.emit(this.selectedMode);
  }

  /**
   * check status of variant-modes of set scenario
   * flag mode as disabled (in disableModes) if either variant is not calculated or not set
   *
   * @param scenario
   */
  verifyModes(): void {
    this.modeStatus = {};
    if (!this.scenario) return;
    this.planningService.getRoutingStatistics().subscribe(stats => {
      for (let mode in this.modes) {
        const variant = this.scenario!.modeVariants.find(mv => mv.mode === Number(mode));
        if (!variant) {
          this.modeStatus[mode] = { enabled: false, message: 'Verkehrsmittelvariante ist nicht verfügbar' };
        }
        else {
          const nRels = stats.nRelsPlaceCellModevariant[variant.variant] || 0;
          this.modeStatus[mode] = { enabled: nRels > 0, message: (nRels === 0)? 'Verkehrsmittelvariante ist nicht berechnet': '' }
        }
      }
      if (this.selectedMode && !this.modeStatus[this.selectedMode]?.enabled) {
        this.changeMode(undefined);
      }
    })
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
