from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EmailEngine:
    """
    A unified engine to handle all marketplace communications.
    """

    @staticmethod
    def _send(subject, recipient_email, template_name, context):
        """HTML template-based email (used for OTP etc.)."""
        try:
            html_content = render_to_string(f'templates/{template_name}.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()  # fix: was missing
            return True
        except Exception as e:
            logger.error(f"EmailEngine._send failed: {str(e)}")
            return False

    @staticmethod
    def _send_plain(subject, recipient_email, body):
        """Plain-text email — used when no HTML template is needed."""
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error(f"EmailEngine._send_plain failed: {str(e)}")
            return False

    @classmethod
    def send_otp(cls, recipient_email, otp, user_name="User"):
        """Sends verification code for Login/Registration."""
        subject = f"{otp} is your verification code"
        context = {
            "otp": otp,
            "user_name": user_name,
            "expiry": "5 minutes"
        }
        return cls._send(subject, recipient_email, "otp_email", context)

    @classmethod
    def send_invoice(cls, recipient_email, order_id, total_amount, items):
        """Sends purchase confirmation to the buyer."""
        subject = f"Invoice for Order #{order_id}"
        context = {
            "order_id": order_id,
            "total": total_amount,
            "items": items,
            "support_email": settings.DEFAULT_FROM_EMAIL
        }
        return cls._send(subject, recipient_email, "invoice_email", context)

    @classmethod
    def send_order_confirmation(cls, recipient_email, order):
        """
        Sent to the buyer immediately after checkout.
        Tells them their order is placed and awaiting payment.
        """
        item_lines = "\n".join(
            f"  - {item.product_name} (SKU: {item.sku}) x{item.quantity} @ ${item.price}"
            for item in order.items.all()
        )
        body = (
            f"Hi,\n\n"
            f"Your order #{order.id} has been placed successfully.\n\n"
            f"Items:\n{item_lines}\n\n"
            f"Order Total: ${order.total}\n"
            f"Shipping to: {order.shipping_address}\n\n"
            f"We will notify you once your payment is confirmed.\n\n"
            f"Thank you for shopping with us!\n"
            f"{settings.DEFAULT_FROM_EMAIL}"
        )
        return cls._send_plain(f"Order #{order.id} Placed", recipient_email, body)

    @classmethod
    def send_payment_confirmed(cls, recipient_email, order):
        """Sent to the buyer when Stripe confirms payment."""
        body = (
            f"Hi,\n\n"
            f"Great news! Payment for your order #{order.id} has been confirmed.\n\n"
            f"Order Total: ${order.total}\n"
            f"Status: {order.get_status_display()}\n\n"
            f"We will update you once your order has been shipped.\n\n"
            f"Thank you!\n"
            f"{settings.DEFAULT_FROM_EMAIL}"
        )
        return cls._send_plain(f"Payment Confirmed — Order #{order.id}", recipient_email, body)

    @classmethod
    def send_order_status_update(cls, recipient_email, order):
        """Sent to the buyer whenever a merchant updates the order status."""
        status_messages = {
            'confirmed': "Your order has been confirmed by the seller.",
            'shipped': "Great news — your order is on its way!",
            'delivered': "Your order has been delivered. Enjoy!",
            'cancelled': "Unfortunately, your order has been cancelled. Contact support if you need help.",
        }
        message = status_messages.get(order.status, f"Your order status has been updated to: {order.get_status_display()}")

        body = (
            f"Hi,\n\n"
            f"Update on your order #{order.id}:\n\n"
            f"{message}\n\n"
            f"Order Total: ${order.total}\n"
            f"Current Status: {order.get_status_display()}\n\n"
            f"Thank you!\n"
            f"{settings.DEFAULT_FROM_EMAIL}"
        )
        return cls._send_plain(f"Order #{order.id} Update — {order.get_status_display()}", recipient_email, body)