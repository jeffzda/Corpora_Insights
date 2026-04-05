---
**Category:** Wind  
**Date Generated:** December 2024  
**Record Count:** 510 records across 17 projects  
**Temporal Coverage:** 2012–2025, with 19 records (3.7%) carrying temporal warnings  

---

# Wind — Delivery Risk Profile

## Executive Summary

Wind projects present a moderate-to-high risk profile characterised by software integration complexity, data measurement challenges, and execution bottlenecks. The highest-risk areas are software & controls (200 adverse records) and grid connection (149 records), driven primarily by forecasting system integration, SCADA complexity, and weak grid interactions. Technical underperformance emerges as the most severe failure mode (18% escalation rate), while data & measurement issues are the most frequent (24% occurrence). Modern projects show improved hardware reliability but heightened software and regulatory complexity.

## Coverage and Data Quality

The profile draws from 17 wind projects spanning 2012–2025, with good temporal distribution: 24 records from early projects (2012–2015), 90 from the development phase (2016–2018), 273 from the mature period (2019–2021), and 123 from recent experience (2022+). Only 3.7% of records carry temporal warnings, indicating most insights remain current. Coverage is particularly strong for advanced forecasting demonstrations, FCAS enablement trials, and hybrid microgrid integration.

## Risk Landscape by Delivery Dimension

**Software & Controls (200 records)** emerges as the highest-risk dimension, dominated by data & measurement failures (33%) and technical underperformance (22%). Modern wind projects involve complex software ecosystems spanning forecasting algorithms, SCADA integration, and grid interface systems. Recent projects demonstrate that machine learning model development, real-time data pipeline management, and API integration with AEMO systems are major delivery challenges.

**Grid Connection (149 records)** ranks second, with balanced exposure across multiple failure modes but particular concentration in data & measurement (21%), technical underperformance (19%), and commercial challenges (14%). Weak grid environments create compound risks where voltage control, FCAS capability, and frequency response interact unpredictably. AEMO integration via MP5F APIs adds regulatory complexity that didn't exist in early wind deployments.

**Design (146 records)** shows heavy exposure to technical underperformance (32%) and data & measurement issues (25%). Modern wind projects face site selection complexity around LIDAR placement, forecast model architecture, and integration with multiple technologies in hybrid configurations. Early ARENA projects experienced wind resource uncertainty, though this has stabilised as measurement techniques matured.

**Procurement (90 records)** is execution-dominated (37% execution & logistics failures), reflecting supply chain vulnerabilities, semiconductor shortages, and specialised equipment sourcing. COVID-19 amplified existing constraints around crane availability, international shipping, and OEM support access for both new and refurbished equipment.

**Construction and Siting** show lower overall exposure but specific challenges: construction is overwhelmingly execution-driven (82%), while siting faces execution challenges (38%) and data quality issues (31%) around resource measurement and environmental constraints.

## Failure Mode Deep-Dive

**Data & Measurement (24% occurrence, 2% severe)** pervades wind project delivery. Recent forecasting projects reveal this encompasses everything from LIDAR placement optimisation to SCADA data quality management. The 2025 Aeolius project found that training ML models on turbine-mounted anemometer data fundamentally limits forecast skill because the relevant meteorological signal occurs upstream. Historical projects struggled with wind resource uncertainty, but this has evolved into sophisticated data pipeline challenges around multi-source integration, spectral analysis for predictability assessment, and real-time data validation.

**Technical Underperformance (20% occurrence, 18% severe)** represents the highest-escalation failure mode. Modern manifestations include FCAS capability constraints at existing wind farms, where voltage management equipment creates unexpected operating envelopes, and sophisticated control system interactions in hybrid microgrids. The Musselroe FCAS trials demonstrated that existing frequency response capability doesn't imply market compliance—extensive control system rework was required. Weak grid environments amplify these challenges by coupling active power and voltage control in ways that standard plant controllers cannot manage.

**Execution & Logistics (14% occurrence, 20% severe)** affects wind projects through specialised equipment constraints and supply chain vulnerabilities. Australia's limited crane availability for wind farm construction creates genuine bottlenecks, while semiconductor shortages severely impacted control system production in recent projects. COVID-19 exposed the fragility of international supply chains for specialised components, with some projects experiencing 18-month delays for electronic components.

**Commercial & Market (12% occurrence, 18% severe)** challenges have evolved from early cost uncertainty to sophisticated market participation complexity. Recent projects demonstrate that improved forecast accuracy doesn't automatically translate to financial benefit—the interaction between FCAS Causer Pays optimisation and technical accuracy creates counterintuitive commercial dynamics that require specialised expertise to navigate.

## Temporal Trends

The wind sector risk profile has fundamentally shifted over the ARENA program period. **Early projects (2012–2018)** were dominated by hardware reliability and resource uncertainty. These risks have largely resolved—modern turbines and measurement techniques are substantially more reliable.

**Recent projects (2019+)** face a different risk landscape centered on software complexity and regulatory integration. The emergence of self-forecasting, FCAS market participation, and hybrid system integration has created new categories of technical and commercial risk. AEMO's dispatch system integration via MP5F APIs introduces dependencies that didn't exist in earlier projects.

**Supply chain risks** intensified dramatically post-2019, with semiconductor shortages and COVID-19 creating unprecedented delays for control systems and specialised components. This trend appears to be stabilising but remains elevated compared to the early program period.

**Regulatory complexity** has increased substantially, with FCAS enablement requiring multi-year testing programs and extensive stakeholder coordination across AEMO, TNSPs, and OEMs. This represents genuinely new risk that early wind projects didn't face.

## Key Watchpoints for Due Diligence

1. **SCADA Integration Complexity**: Probe the specific SCADA architecture and data historian capabilities. Projects consistently underestimate the effort required for real-time data integration, particularly for self-forecasting systems. Verify 1-minute data logging is already operational—retrofitting this capability delays model development.

2. **Supply Chain Resilience**: For any project requiring specialised control systems, semiconductor components, or international OEM support, validate supply chain robustness and build substantial schedule contingency. Recent projects experienced 18-month delays for electronic components.

3. **Grid Strength Assessment**: For connection points with SCR below 3, assess whether the voltage management requirements will constrain future FCAS or advanced control capabilities. Weak grid sites require substantially more complex plant control systems that may limit operational flexibility.

4. **Forecasting Architecture**: If the project includes self-forecasting, validate that the model development approach accounts for curtailment, turbine outages, and site-specific constraints. Many technically superior models fail commercially because they don't handle operational realities.

5. **Multi-Technology Integration**: For hybrid projects, verify that a single party has overall control system architecture responsibility. Split-contractor models consistently create coordination failures at the system integration level.

6. **OEM Control System Access**: Confirm that turbine and inverter OEMs will provide full access to control system parameters and detailed models. IP restrictions on control system access consistently delay FCAS enablement and performance optimisation.

7. **Regulatory Pathway Validation**: For any project involving FCAS capability, hybrid registration, or novel grid connection arrangements, validate the regulatory pathway early with AEMO. Precedent-setting projects require substantially longer approval timelines than anticipated.