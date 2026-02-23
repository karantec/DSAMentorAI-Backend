from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
import razorpay
import hmac
import hashlib
import os

payments_bp = Blueprint("payments", __name__)

rzp = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)

# Plan prices in paise (₹199 = 19900 paise)
PLANS = {
    "pro": {
        "name":   "Pro Plan",
        "amount": 19900,
        "label":  "₹199/month — Unlimited access",
    },
    "premium": {
        "name":   "DSA Premium",
        "amount": 49900,
        "label":  "₹499/month — Everything + Mock Interviews",
    }
}


def get_db():
    return current_app.db


@payments_bp.route("/create-order", methods=["POST"])
@jwt_required()
def create_order():
    """Create a Razorpay order for one-time payment."""
    data     = request.get_json()
    plan_key = data.get("plan")

    if plan_key not in PLANS:
        return jsonify({"error": "Invalid plan"}), 400

    plan = PLANS[plan_key]

    try:
        order = rzp.order.create({
            "amount":   plan["amount"],
            "currency": "INR",
            "notes": {
                "plan": plan_key,
            }
        })

        return jsonify({
            "order_id":   order["id"],
            "amount":     plan["amount"],
            "currency":   "INR",
            "plan_name":  plan["name"],
            "razorpay_key": os.getenv("RAZORPAY_KEY_ID"),
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@payments_bp.route("/verify", methods=["POST"])
@jwt_required()
def verify_payment():
    """Verify payment signature and upgrade user plan."""
    db      = get_db()
    user_id = get_jwt_identity()
    data    = request.get_json()

    payment_id = data.get("razorpay_payment_id")
    order_id   = data.get("razorpay_order_id")
    signature  = data.get("razorpay_signature")
    plan_key   = data.get("plan")

    # Verify signature
    message  = f"{order_id}|{payment_id}"
    expected = hmac.new(
        os.getenv("RAZORPAY_KEY_SECRET").encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    if expected != signature:
        return jsonify({"error": "Payment verification failed"}), 400

    # Upgrade user in DB
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"plan": plan_key}}
    )

    return jsonify({
        "message": f"🎉 You're now on {PLANS[plan_key]['name']}!",
        "plan": plan_key,
    }), 200


@payments_bp.route("/plans", methods=["GET"])
def get_plans():
    """Return plan info for frontend."""
    return jsonify({
        "plans": [
            {
                "key":    "free",
                "name":   "Free",
                "price":  "₹0",
                "amount": 0,
                "color":  "gray",
                "features": [
                    "5 doubts per day",
                    "All 4 AI tools",
                    "Basic explanations",
                ]
            },
            {
                "key":    "pro",
                "name":   "Pro",
                "price":  "₹199/mo",
                "amount": 19900,
                "color":  "green",
                "features": [
                    "Unlimited doubts",
                    "All 4 AI tools",
                    "Priority AI responses",
                    "Doubt history saved",
                ]
            },
            {
                "key":    "premium",
                "name":   "DSA Premium",
                "price":  "₹499/mo",
                "amount": 49900,
                "color":  "yellow",
                "features": [
                    "Everything in Pro",
                    "Unlimited Mock Interviews",
                    "Personalized roadmap",
                    "Interview feedback reports",
                    "WhatsApp doubt support",
                ]
            },
        ]
    }), 200