from __future__ import annotations

from typing import Any, Literal, TypedDict


# Response lines


class ResponseLinesDiscoveryList(TypedDict):
    LinesDelivery: LinesDelivery


class LinesDelivery(TypedDict):
    ResponseTimestamp: str
    RequestMessageRef: str | None
    ValidUntil: str
    ShortestPossibleCycle: str
    AnnotatedLineRef: list[AnnotatedLineStructure] | None


class AnnotatedLineStructure(TypedDict):
    LineRef: str | None
    LineName: str | None
    Destinations: list[AnnotatedDestinationStructure] | None
    Extension: ExtensionAnnotatedLineStructure


class AnnotatedDestinationStructure(TypedDict):
    DirectionRef: int
    DestinationName: Any


class ExtensionAnnotatedLineStructure(TypedDict):
    RouteType: Literal["bus", "tram", "undefined"]
    RouteColor: str | None
    RouteTextColor: str | None


# Response stops


class ResponseStopPointsDiscoveryList(TypedDict):
    StopPointsDelivery: StopPointsDelivery


class StopPointsDelivery(TypedDict):
    ResponseTimestamp: str
    RequestMessageRef: str | None
    AnnotatedStopPointRef: list[AnnotatedStopPointStructure] | None


class AnnotatedStopPointStructure(TypedDict):
    StopPointRef: str | None  # Unique reference of the stop
    Lines: list[AnnotatedLineStructure] | None
    Location: Location
    StopName: str | None
    Extension: ExtensionAnnotatedStopPointStructure


class Location(TypedDict):
    Longitude: int | None
    Latitude: int | None


class ExtensionAnnotatedStopPointStructure(TypedDict):
    StopCode: str | None  # Client stop code, recommendated (cts api doc :) to request the StopMonitoring API. This code identify the stop with a precise direction ("one side" of the road).
    LogicalStopCode: str | None
    IsFlexhopStop: bool
    distance: int | None


# Response stop monitoring


class ResponseStopMonitoringList(TypedDict):
    ServiceDelivery: ServiceDelivery


class ServiceDelivery(TypedDict):
    ResponseTimestamp: str
    RequestMessageRef: str | None
    StopMonitoringDelivery: list[StopMonitoringDelivery] | None
    VehicleMonitoringDelivery: list[VehicleMonitoringDelivery] | None
    EstimatedTimetableDelivery: list[EstimatedTimetableDelivery] | None
    GeneralMessageDelivery: list[GeneralMessageDelivery] | None


class StopMonitoringDelivery(TypedDict):
    version: str | None
    ResponseTimestamp: str
    ValidUntil: str
    ShortestPossibleCycle: str
    MonitoringRef: Any | None
    MonitoredStopVisit: list[MonitoredStopVisit]


class MonitoredStopVisit(TypedDict):
    RecordedAtTime: str
    MonitoringRef: str | None
    StopCode: str | None
    MonitoredVehicleJourney: MonitoredVehicleJourney


class MonitoredVehicleJourney(TypedDict):
    LineRef: str | None
    DirectionRef: int
    FramedVehicleJourneyRef: FramedVehicleJourneyRef
    VehicleMode: Literal["bus", "tram", "coach", "undefined"]
    PublishedLineName: str | None
    DestinationName: str | None
    DestinationShortName: str | None
    Via: str | None
    MonitoredCall: MonitoredCall


class FramedVehicleJourneyRef(TypedDict):
    DatedVehicleJourneySAERef: str | None


class MonitoredCall(TypedDict):
    StopPointName: str | None
    StopCode: str | None
    Order: int | None
    ExpectedDepartureTime: str | None
    ExpectedArrivalTime: str
    Extension: ExtensionMonitoredCall
    PreviousCall: list[PreviousCall] | None
    OnwardCall: list[OnwardCall] | None


class ExtensionMonitoredCall(TypedDict):
    IsRealTime: bool
    DataSource: str | None


class PreviousCall(TypedDict):
    StopPointName: str | None
    StopCode: str | None
    Order: int | None


class OnwardCall(TypedDict):
    StopPointName: str | None
    StopCode: str | None
    Order: int | None
    ExpectedDepartureTime: str | None
    ExpectedArrivalTime: str


class VehicleMonitoringDelivery(TypedDict):
    ResponseTimestamp: str
    ValidUntil: str
    ShortestPossibleCycle: str
    VehicleActivity: list[VehicleActivity] | None


class VehicleActivity(TypedDict):
    RecordedAtTime: str
    MonitoredVehicleJourney: MonitoredVehicleJourney


class EstimatedTimetableDelivery(TypedDict):
    version: str | None
    ResponseTimestamp: str
    ValidUntil: str
    ShortestPossibleCycle: str
    EstimatedJourneyVersionFrame: list[EstimatedJourneyVersionFrame] | None


class EstimatedJourneyVersionFrame(TypedDict):
    RecordedAtTime: str
    EstimatedVehicleJourney: list[EstimatedVehicleJourney]


class EstimatedVehicleJourney(TypedDict):
    LineRef: str | None
    DirectionRef: int
    FramedVehicleJourneyRef: FramedVehicleJourneyRef
    PublishedLineName: str | None
    IsCompleteStopSequence: bool
    EstimatedCalls: list[EstimatedCalls] | None
    Extension: ExtensionEstimatedVehicleJourney


class ExtensionEstimatedVehicleJourney(TypedDict):
    VehicleMode: Literal["bus", "tram", "coach", "undefined"]


class EstimatedCalls(TypedDict):
    StopLineRef: str | None
    StopPointName: str | None
    DestinationName: str | None
    DestinationShortName: str | None
    Via: str | None
    ExpectedDepartureTime: str | None
    ExpectedArrivalTime: str
    Extension: ExtensionEstimatedCalls


class ExtensionEstimatedCalls(TypedDict):
    IsRealTime: bool
    IsCheckOut: bool
    quay: str | None
    DataSource: str | None


class GeneralMessageDelivery(TypedDict):
    version: str | None
    ResponseTimestamp: str
    ShortestPossibleCycle: str
    InfoMessage: list[InfoMessage] | None


class InfoMessage(TypedDict):
    formatRef: str | None
    RecordedAtTime: str
    ItemIdentifier: str | None
    InfoMessageIdentifier: str | None
    InfoChannelRef: str | None
    ValidUntilTime: str
    Content: CTSGeneralMessage


class CTSGeneralMessage(TypedDict):
    ImpactStartDateTime: str
    ImpactEndDateTime: str | None
    ImpactedGroupOfLinesRef: str | None
    ImpactedLineRef: list[str] | None
    TypeOfPassengerEquipmentRef: str | None
    Priority: Literal["Normal", "Urgent", "Extrem"]
    SendUpdatedNotificationsToCustomers: bool
    Message: list[Message] | None


class Message(TypedDict):
    MessageZoneRef: str | None
    MessageText: list[MessageText] | None


class MessageText(TypedDict):
    Value: str | None
    Lang: Literal["FR", "EN", "DE"]
