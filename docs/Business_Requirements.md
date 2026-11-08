# Business Requirements – OPS System Management Software

*Draft. Detailed business rules, workflows and design decisions are documented separately.*

## 1. Business Model

The business provides end-to-end maintenance services for clients’ devices, covering both hardware and software maintenance throughout the device lifecycle.

Most devices are owned by clients. The business also owns a pool of devices that it rents to clients who prefer not to purchase them.

## 2. Business Operations

To fulfil its business objectives, the organization operates through different departments/modules, each responsible for specific activities within the device maintenance lifecycle.

As devices progress through these operational stages, their movement, status and the activities performed must be recorded and traceable throughout the process.

**Scope.** A single service provider operates the system. Use by several providers is out of scope.

## 3. Device Lifecycle

A device moves through the stages below. Each stage has one owning department. The rental stage applies only to devices owned by the service provider.

### 3.1 Registration

New devices are produced under a production batch. A production batch belongs to exactly one client and one model version, has a unique batch code, and that batch code forms part of every serial number in the batch. Warehouse records the client, model, version and batch code, then scans the serial numbers to register the devices. Once registered, a device’s ownership is determined through its production batch and does not change.

### 3.2 Configuration and dispatch

Warehouse sends new devices to Production. Production installs and configures the software, prepares the devices and dispatches them to the client. Dispatched devices have the status Shipped.

### 3.3 In the field

In the field a device normally progresses from Shipped to Installed to Activated. Installation and activation usually happen remotely after the client contacts the provider. A device may stay in any of these statuses without it being a problem. It becomes a Finance matter only when a device is stuck because the client has not provided the documents or confirmation required. How these statuses are recorded is outside the current scope (see Open Items).

### 3.4 Rentals (provider-owned devices only)

Finance tells Warehouse which serial numbers to rent out. Warehouse assigns them to a client with a start date and an expected return date. Only devices owned by the service provider can be rented, and a device can have only one active rental at a time. Renting never changes who owns the device. While a rental is active, the renting client is treated as the client for operational purposes.

A rental ends only when the device comes back to Warehouse, where the agent records the end date. A rental cannot end while the device is on a processing line such as Repairs or Production. Rentals that are overdue or near their due date must be surfaced and escalated to Finance. The near-due window depends on contract terms and must be changeable without code changes.

### 3.5 Return

Devices come back because they need maintenance, because a contract has been terminated or has ended, or because a rental has ended. Warehouse is the only department that receives returns.

- Warehouse first records the return batch (the batch number under which the devices arrive), then scans each serial number.
- A serial number that is not registered in the system is given the status Unknown/Not Assigned and is not processed further.
- Devices with the status Returning go to Repairs. Devices returned directly by a client, for example because a contract has ended, may arrive with other statuses (such as Installed, Activated or Shipped) that Finance needs to investigate. Such a serial number is escalated to Finance and cannot be processed to Repairs until Finance resolves its status. No physical device goes to Finance.
- A rented device cannot pass without its rental being checked. An overdue rental blocks the device until Warehouse ends the rental.
- Devices that pass these checks are processed as normal returns.

The return batch number is separate from the production batch code. A client may supply its own batch number when returning devices; otherwise the business assigns one. One return batch can cover many devices.

### 3.6 Assessment and repair

Repairs only works on devices that Warehouse has verified; for any other serial number it shows that the device has not been processed in Warehouse. Repairs assesses each device as passed or failed. For a failed device Repairs records the faults, the parts needed, the quantities and a photo of the device’s condition. Each fault maps to a fixed part. These records form the device’s permanent repair history.

Whether a parts request may go ahead depends on the commercial terms:

- **Standard devices:** if the cost of the parts is within what the client has agreed to pay, the request proceeds to Stores. If it is above that amount, the device is held until Finance decides.
- **Project devices** (covered by a special contract): the request proceeds only after the client approves a quotation that Finance generates and sends. If the quotation is not approved, the device stays as it is with the status Not Approved.

Repairs assesses several devices before requesting parts, and requests go to Stores in batches. If a required part is out of stock, the device waits in Repairs with the status Awaiting Parts until Stores has stock again, and Repairs is notified. If a device cannot be repaired, the unused parts are returned to Stores.

### 3.7 Return to the client

Repaired devices go to Production, which scans and validates them on arrival, re-configures them as needed and dispatches them to the client. Production sends any device found faulty during configuration back to Repairs. A return batch stays open while any of its devices are still in the process, and closes when the last expected device has been validated at Production.

### 3.8 End of life

When a client discontinues a model, it scraps the devices instead of transferring them to another client. A device can be marked as scrapped or decommissioned. Its data is kept.

## 4. Departments / Modules

1. Warehouse
2. Repairs
3. Production (Configuration and Dispatch)
4. Small Parts Stores
5. Finance

A customer-support module is a planned addition and is listed under Open Items.

## 5. Departmental / Module Responsibilities

### 1. Warehouse

- Registering clients, models, versions and production batches, and linking batch codes to clients and models.
- Registering new devices by scanning their serial numbers against their batch.
- Correcting mistakes in client, model, version and batch-code data.
- Sending new devices to Production for configuration.
- Receiving returned devices: recording the return batch, scanning and validating serial numbers, escalating devices to Finance where required and applying rental checks.
- Managing rentals: assigning provider-owned devices to clients and ending rentals when devices come back.
- Serving as the source of truth for whether a device has been verified through Warehouse.

### 2. Repairs

- Confirming that a device has been verified by Warehouse before assessing it.
- Assessing devices and recording faults, parts, quantities and a photo of the device’s condition.
- Requesting parts from Small Parts Stores in batches, and managing devices held for a Finance decision, client approval or missing parts.
- Recording repair activities and outcomes as a permanent repair history for each device.
- Sending repaired devices to Production and supplying repair data to Finance for billing.

### 3. Production

- Scanning and validating devices on arrival.
- Configuring devices, including software installation and configuration.
- Preparing and dispatching devices to clients.
- Sending devices found faulty during configuration back to Repairs.

### 4. Small Parts Stores

- Managing small parts inventory and stock levels.
- Receiving and recording incoming parts.
- Processing parts requests and issuing parts to support repair activities.
- Tracking parts usage.
- Notifying Repairs when a part that was out of stock becomes available.
- Receiving back unused parts when a device could not be repaired.

### 5. Finance

- Managing billing for services rendered to clients.
- Sending Warehouse the serial numbers of devices to be rented out.
- Resolving escalations raised by Warehouse for returned devices.
- Deciding on devices that Repairs holds because the parts cost is above the agreed amount.
- Generating and sending quotations for project devices and recording the client’s decision.
- Advising Repairs when contractual terms or service agreements change for a client’s devices.

## 6. Departmental / Module Relationships

| Department / Module | Supported by | What they do for it | Physical items | Information exchanged |
| --- | --- | --- | --- | --- |
| **Warehouse** | Finance | Resolves escalations raised by Warehouse | None | Resolutions to escalated issues |
| | Finance | Sends serial numbers for rental assignments | None | Serial numbers of devices to be rented out |
| **Repairs** | Warehouse | Sends returning devices that need maintenance | Returning devices | Serial numbers of returning devices |
| | Finance | Handles billing for repairs | None | Repairs data |
| | Finance | Decides on held devices and reports quotation outcomes | None | Approval decisions, quotation outcomes |
| | Finance | Advises on repair conditions when contract terms change | None | Repair conditions under the new contract terms |
| | Small Parts Stores | Fulfils parts requests and signals restocked parts | Requested parts | Parts request data, stock availability |
| | Production | Sends back devices found faulty during configuration | Faulty devices | Fault description recorded during configuration (proposed) |
| **Production** | Repairs | Sends repaired devices | Repaired devices | Serial numbers of the repaired devices |
| | Warehouse | Sends new devices for configuration and preparation | New devices | Serial numbers of the new devices |
| **Small Parts Stores** | Repairs | Returns ordered parts when a device could not be repaired | Unused ordered parts | Part, quantity and repair record reference (proposed) |
| **Finance** | Repairs | Supplies repairs data for billing | None | Repairs data for billing |
| | Warehouse | Raises escalations for returned devices | None | Serial number and its status |

## 7. Clients and Ownership

- A client is an external customer, not an internal department. Clients own devices, receive them, return them and may supply their own batch number on return.
- Every device belongs to a client through its production batch. The service provider is itself registered as a client, and its devices are the provider-owned devices that can be rented.
- The operational client of a device is the renting client while a rental is active, and the owning client otherwise. Repairs bills this client and Production configures devices for this client.
- Whether a device is a project device is set by contract terms and recorded on its production batch.

## 8. Service Levels

The service-level clock for a returning device starts when its return batch is created. Targets are configurable per department; for example, Warehouse 2 days, Repairs 5 days and Production 3 days. The clock keeps running during a Finance escalation or while a device is Awaiting Parts. These events are recorded in the logs but do not pause the clock.

## 9. Data and Access Principles

- Access is by department: users sign in and can use only the functions of their own department.
- Every scanned serial number is checked against the registered devices, in every department.
- Departments do not change the core device record. Each department keeps its own record of what it did and reads the device record for reference.
- Device movement, status changes and department activities are recorded and traceable. Corrections to client, model, version and batch-code data are applied directly, and their history is not kept.
- Data is not deleted by default, including data for clients that are no longer served. No role currently has permission to delete data.
- Business parameters that depend on contracts, such as the near-due rental window, must be changeable without code changes.

## 10. Open Items

1. **Customer support module (planned).** It affects how a device gets the Returning status and how installation and activation in the field are recorded.
2. **Finance approval path.** How Finance resolves a held above-threshold device, who is allowed to approve, and how Finance is notified are not yet specified.
3. **Information exchanged.** The fault information sent from Production to Repairs, and the details of unused parts returned to Stores, are proposals.
4. **Serial number format.** The current format (batch code, hyphen, device id) is the system’s own design. Supporting external numbering standards, and how repeat batches for the same client, model and version are identified, are future considerations.