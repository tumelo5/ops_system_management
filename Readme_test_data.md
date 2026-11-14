## Testing the system

Once the system is running, you can build a small test dataset through the UI by following the steps below. All names and codes are fictional.

### 1. Log in

On the login page, use the **Demo Access** panel: click a department to auto-fill its credentials, then *Sign in*. No account setup is needed.

**Scope:** the Warehouse module is fully working, so use **Warehouse** for the steps below. Repairs, Stores and Finance are designed (see `/docs`) but not yet implemented. You can still sign in as them to see department-based access control: they cannot open Warehouse screens.

### 2. Test data

**Clients** (step 1)

| Client          |
|-----------------|
| Demo Service Co |
| Alpha Retail    |
| Beacon Foods    |
| Cedar Pharmacy  |

Demo Service Co stands in for the servicing company. Only its devices can be rented out.

**Batches** (step 2)

| Batch code | Client          | Model      | Version | Devices to scan |
|------------|-----------------|------------|---------|-----------------|
| DEMO001    | Demo Service Co | Terminal X | v1      | 6               |
| DEMO002    | Alpha Retail    | Terminal X | v1      | 3               |
| DEMO003    | Beacon Foods    | Terminal Y | v1      | 3               |

DEMO001 creates the model and version. DEMO002 reuses the same model and version, so select them from the dropdown instead of typing them again.

The device counts are only a suggestion. There is no limit on how many devices you can scan per batch, so feel free to scan more.

**Serial numbers.** The system matches a scanned serial number to its batch by checking that the serial number **starts with** an existing batch code, so serial numbers of any length work. For this demo, each serial number is the batch code followed by a unique device ID:

| Batch code | + Unique device ID | = Serial number to scan    |
|------------|--------------------|----------------------------|
| DEMO001    | 01 to 06           | `DEMO00101` to `DEMO00106` |
| DEMO002    | 01 to 03           | `DEMO00201` to `DEMO00203` |
| DEMO003    | 01 to 03           | `DEMO00301` to `DEMO00303` |

For example, `DEMO00101` is batch `DEMO001` plus unique device ID `01`.

Input is case-insensitive: batch codes, serial numbers and names are normalised to lowercase, so `DEMO00101` is stored as `demo00101`.

**Rentals** (used in step 4). Dates are relative to the day you test:

| Device      | Rented to      | Start date   | Expected return |
|-------------|----------------|--------------|-----------------|
| `DEMO00101` | Alpha Retail   | today - 20 d | today + 40 d    |
| `DEMO00102` | Beacon Foods   | today - 55 d | today + 5 d     |
| `DEMO00103` | Cedar Pharmacy | today - 90 d | today - 7 d     |

### 3. Build the data

Warehouse → Clients & Batches. The workflow has three steps:

1. **Client creation:** add the clients from the table above and save.
2. **Linking:** select a client, then create the batch with its model and version.
   - New model or version: type it, and enter the batch code.
   - Model and version that already exist: select them from the dropdown.
   - Do this for all three batches.
3. **Device scanning:** scan or type the batch's serial numbers and press Enter. Each scan is validated and saved immediately, so there is no confirm or save step. The result of each scan is shown right away: `<serial number>: success`, or the reason it was rejected.

Things to try:

- **Duplicate:** scan `DEMO00101` again. It is rejected as already existing, and nothing is duplicated.
- **Unknown batch:** scan `NOPE01`. It is rejected because no batch code matches the start of the serial number.

### 4. Rentals

1. **Assign Rental:** choose the client, scan the serial numbers from the rentals table, set the dates, and submit.
2. **Guards to try:**
   - Rent `DEMO00101` a second time: rejected (one active rental per device).
   - Rent `DEMO00201`: rejected (client-owned, not rentable).
3. **End Rental:** scan `DEMO00101`, review the active rental that appears, and pick an end date.

### 5. Tests

```bash
python manage.py test        # backend, including the rental suite
npx playwright test          # end-to-end
```

### Resetting

To start over with a clean database: `docker compose down -v`, then restart and run migrations again.