# api_gateway – Odoo 19 HTTP REST Endpoints

Custom module that exposes **HTTP GET endpoints** for core Inventory, Purchase,
and Employee Purchase Requisition models.  
All responses return **JSON over HTTP** (`application/json`).

---

## Module Structure

```
api_gateway/
├── __init__.py
├── __manifest__.py
├── security/
│   └── ir.model.access.csv
└── controllers/
    ├── __init__.py
    ├── main.py          ← shared helpers + health-check
    ├── inventory.py     ← products, categories, UoM, stock
    ├── purchase.py      ← purchase orders
    └── requisition.py   ← employee purchase requisitions
```

---

## Dependencies

Add these to `depends` in `__manifest__.py` (already done):

| Module | Purpose |
|---|---|
| `product` | product.template, product.category |
| `uom` | uom.uom |
| `stock` | stock.picking, stock.move, stock.location |
| `purchase` | purchase.order |
| `employee_purchase_requisition` | your custom req module |

---

## All Endpoints

### Health Check
| Method | Route | Description |
|---|---|---|
| GET | `/api/v1` | Lists all available endpoints |

### Products (`product.template`)
| Method | Route | Query Params |
|---|---|---|
| GET | `/api/v1/products` | `name`, `default_code`, `categ_id`, `type`, `active`, `limit`, `offset` |
| GET | `/api/v1/products/<id>` | – |

### Categories (`product.category`)
| Method | Route | Query Params |
|---|---|---|
| GET | `/api/v1/categories` | `name`, `limit`, `offset` |
| GET | `/api/v1/categories/<id>` | – |

### Units of Measure (`uom.uom`)
| Method | Route | Query Params |
|---|---|---|
| GET | `/api/v1/uom` | `name`, `category`, `limit`, `offset` |
| GET | `/api/v1/uom/<id>` | – |

### Stock Pickings (`stock.picking`)
| Method | Route | Query Params |
|---|---|---|
| GET | `/api/v1/stock/pickings` | `name`, `state`, `picking_type_id`, `partner_id`, `origin`, `limit`, `offset` |
| GET | `/api/v1/stock/pickings/<id>` | Returns picking **+ its stock.move lines** |

### Stock Moves (`stock.move`)
| Method | Route | Query Params |
|---|---|---|
| GET | `/api/v1/stock/moves` | `picking_id`, `product_id`, `state`, `limit`, `offset` |

### Stock Locations (`stock.location`)
| Method | Route | Query Params |
|---|---|---|
| GET | `/api/v1/stock/locations` | `name`, `usage`, `active`, `limit`, `offset` |
| GET | `/api/v1/stock/locations/<id>` | – |

### Purchase Orders (`purchase.order`)
| Method | Route | Query Params |
|---|---|---|
| GET | `/api/v1/purchase/orders` | `name`, `state`, `partner_id`, `origin`, `date_from`, `date_to`, `limit`, `offset` |
| GET | `/api/v1/purchase/orders/<id>` | Returns PO **+ order lines** |

### Employee Purchase Requisitions
| Method | Route | Query Params |
|---|---|---|
| GET | `/api/v1/purchase/requisitions` | `name`, `state`, `employee_id`, `department_id`, `date_from`, `date_to`, `limit`, `offset` |
| GET | `/api/v1/purchase/requisitions/<id>` | Returns requisition **+ lines** |

---

## Response Format

```json
{
  "status": "success",
  "count": 3,
  "data": [ ... ]
}
```

Error response:
```json
{
  "status": "error",
  "message": "Product not found"
}
```

---

## Authentication

All routes use `auth='user'` → the caller must be **logged in** to Odoo
(session cookie or HTTP Basic Auth with Odoo credentials).

To switch to API-key auth (Odoo 16+) change `auth='user'` → `auth='api_key'`.  
To make endpoints public (no auth) change to `auth='public'` ⚠️ use with caution.

---

## Important Notes for `employee.purchase.requisition`

The `requisition.py` controller uses **auto-detection** for:
- The model name (`employee.purchase.requisition`, `hr.purchase.requisition`, …)
- The lines field (`line_ids`, `requisition_line_ids`, …)
- Common field name variants

If your module uses **different field names**, update `_serialize_req_line()`
and `_serialize_requisition()` in `controllers/requisition.py`.

---

## Installation

1. Copy the `api_gateway` folder to your Odoo `addons` path.
2. Restart Odoo server.
3. Go to **Apps → Update Apps List**.
4. Search for **API Gateway** and click **Install**.

---

## Example Requests

```bash
# Health check
curl -u admin:admin http://localhost:8069/api/v1

# All products (first 10)
curl -u admin:admin "http://localhost:8069/api/v1/products?limit=10"

# Products filtered by category
curl -u admin:admin "http://localhost:8069/api/v1/products?categ_id=5"

# Single product
curl -u admin:admin http://localhost:8069/api/v1/products/42

# Stock pickings in 'done' state
curl -u admin:admin "http://localhost:8069/api/v1/stock/pickings?state=done&limit=20"

# Picking detail with moves
curl -u admin:admin http://localhost:8069/api/v1/stock/pickings/15

# Purchase orders between dates
curl -u admin:admin "http://localhost:8069/api/v1/purchase/orders?date_from=2025-01-01&date_to=2025-12-31"

# Requisitions by employee
curl -u admin:admin "http://localhost:8069/api/v1/purchase/requisitions?employee_id=7"
```
