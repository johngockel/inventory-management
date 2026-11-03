from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, timedelta
from typing import List, Optional
from pydantic import BaseModel
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str
    unit_cost: float
    lead_time_days: int
    supplier: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrderLine(BaseModel):
    sku: str
    name: str
    supplier: str
    quantity: int
    unit_cost: float
    line_total: float
    lead_time_days: int

class PurchaseOrder(BaseModel):
    id: str
    order_number: str
    items: List[PurchaseOrderLine]
    total_cost: float
    lead_time_days: int
    status: str
    submitted_date: str
    expected_delivery_date: str
    # Set when the order was raised from a backlog row; None for restocking-page orders
    backlog_item_id: Optional[str] = None

class PurchaseOrderLineRequest(BaseModel):
    sku: str
    quantity: int

class CreatePurchaseOrderRequest(BaseModel):
    items: List[PurchaseOrderLineRequest]
    backlog_item_id: Optional[str] = None

class Task(BaseModel):
    id: int
    title: str
    priority: str
    dueDate: str
    status: str

class CreateTaskRequest(BaseModel):
    title: str
    priority: str = "medium"
    dueDate: str

# Tasks live in memory only. Ids are assigned from a counter, so they keep
# increasing for the life of the process. The frontend keeps mock tasks
# (from useAuth) separately, with their own small integer ids.
tasks: List[dict] = []
_next_task_id = 1000

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        # Restocking orders carry no backlog_item_id, so use .get() to skip them safely
        has_po = any(po.get("backlog_item_id") == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.get("/api/purchase-orders", response_model=List[PurchaseOrder])
def get_purchase_orders():
    """Get submitted restocking orders, newest first"""
    return list(reversed(purchase_orders))

@app.post("/api/purchase-orders", response_model=PurchaseOrder, status_code=201)
def create_purchase_order(body: CreatePurchaseOrderRequest):
    """Submit a restocking order.

    Only SKU and quantity are accepted from the client. Unit cost and lead time
    are looked up server-side from the demand forecast so the client cannot
    submit a lower price than the catalogue value.
    """
    if not body.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    skus = [line.sku for line in body.items]
    if len(set(skus)) != len(skus):
        raise HTTPException(status_code=400, detail="Each SKU may appear only once per order")

    lines = []
    for req in body.items:
        if req.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Quantity for {req.sku} must be greater than 0")
        forecast = next((f for f in demand_forecasts if f["item_sku"] == req.sku), None)
        if forecast is None:
            raise HTTPException(status_code=400, detail=f"Unknown SKU: {req.sku}")
        lines.append({
            "sku": forecast["item_sku"],
            "name": forecast["item_name"],
            "supplier": forecast["supplier"],
            "quantity": req.quantity,
            "unit_cost": forecast["unit_cost"],
            "line_total": round(req.quantity * forecast["unit_cost"], 2),
            "lead_time_days": forecast["lead_time_days"],
        })

    # The order arrives when the slowest supplier delivers
    lead_time = max(line["lead_time_days"] for line in lines)
    today = date.today()
    order_number = f"PO-{len(purchase_orders) + 1:05d}"
    order = {
        "id": str(len(purchase_orders) + 1),
        "order_number": order_number,
        "items": lines,
        "total_cost": round(sum(line["line_total"] for line in lines), 2),
        "lead_time_days": lead_time,
        "status": "Submitted",
        "submitted_date": today.isoformat(),
        "expected_delivery_date": (today + timedelta(days=lead_time)).isoformat(),
        "backlog_item_id": body.backlog_item_id,
    }
    purchase_orders.append(order)
    return order

@app.get("/api/tasks", response_model=List[Task])
def get_tasks():
    """Get all in-memory tasks, newest first"""
    return list(reversed(tasks))

@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(body: CreateTaskRequest):
    """Create a task. New tasks are returned with status 'pending'."""
    global _next_task_id
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Task title must not be empty")
    if body.priority not in ("high", "medium", "low"):
        raise HTTPException(status_code=400, detail="Priority must be high, medium or low")
    task = {
        "id": _next_task_id,
        "title": title,
        "priority": body.priority,
        "dueDate": body.dueDate,
        "status": "pending",
    }
    _next_task_id += 1
    tasks.append(task)
    return task

@app.patch("/api/tasks/{task_id}", response_model=Task)
def toggle_task(task_id: int):
    """Toggle a task between 'pending' and 'completed'."""
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task["status"] = "completed" if task["status"] == "pending" else "pending"
    return task

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    """Delete a task by id."""
    index = next((i for i, t in enumerate(tasks) if t["id"] == task_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    tasks.pop(index)
    return {"deleted": task_id}

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

def _filtered_orders(warehouse: Optional[str], category: Optional[str],
                     status: Optional[str], month: Optional[str]) -> list:
    """Orders matching the global filter bar, shared by all report endpoints"""
    filtered = apply_filters(orders, warehouse, category, status)
    return filter_by_month(filtered, month)

@app.get("/api/reports/quarterly")
def get_quarterly_reports(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get quarterly performance reports"""
    # Calculate quarterly statistics from orders
    quarters = {}

    for order in _filtered_orders(warehouse, category, status, month):
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get month-over-month trends"""
    months = {}

    for order in _filtered_orders(warehouse, category, status, month):
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
