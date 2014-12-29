import pytz
from datetime import datetime
from decimal import Decimal, ROUND_UP, ROUND_DOWN
from django.core.mail import mail_admins
from django.db import models
from django_extensions.db.models import TimeStampedModel
from accounts.models import Address
from finance.models import Balance
from mailing.helpers import mail_user, get_template_by_id, render_mail_template
from ordering.core import get_or_create_order, get_current_order_round
from django.conf import settings

ORDER_CONFIRM_MAIL_ID = 12


class Supplier(TimeStampedModel):
    class Meta:
        verbose_name = "Leverancier"

    name = models.CharField(max_length=50, unique=True)
    address = models.ForeignKey(Address)
    email = models.EmailField()
    biography = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)

    def __unicode__(self):
        return self.name

    def has_orders_in_current_order_round(self):
        return OrderProduct.objects.filter(product__supplier=self,
                                           order__order_round=get_current_order_round()).exists()


class OrderRound(TimeStampedModel):
    class Meta:
        verbose_name = "Bestelronde"
        verbose_name_plural = "Bestelronden"

    open_for_orders = models.DateTimeField()
    closed_for_orders = models.DateTimeField()
    collect_datetime = models.DateTimeField()
    # TODO: Set default values to the values of previous object
    markup_percentage = models.DecimalField(decimal_places=2, max_digits=5, default=7.0)
    transaction_costs = models.DecimalField(decimal_places=2, max_digits=5, default=0.35)
    order_placed = models.BooleanField(default=False)
    suppliers_reminder_sent = models.BooleanField(default=False)

    def is_not_open_yet(self):
        current_datetime = datetime.now(pytz.utc)  # Yes, UTC. see Django's timezone docs
        return current_datetime < self.open_for_orders

    @property
    def is_open(self):
        current_datetime = datetime.now(pytz.utc)  # Yes, UTC. see Django's timezone docs
        return current_datetime >= self.open_for_orders and current_datetime < self.closed_for_orders

    def is_current(self):
        return self == get_current_order_round()

    def __unicode__(self):
        return "Bestelronde #%s" % self.pk


class OrderManager(models.Manager):
    use_for_related_fields = True

    def get_current_order(self):
        try:
            return super(OrderManager, self).get_queryset().filter(finalized=False,
                                                                   user=self.instance,
                                                                   order_round=get_current_order_round()).order_by('-pk')[0]
        except IndexError:
            return get_or_create_order(user=self.instance)

    def get_last_finalized_order(self):
        return super(OrderManager, self).get_queryset().filter(finalized=True,
                                                               user=self.instance,
                                                               order_round=get_current_order_round()).order_by('-pk')[0]


class Order(TimeStampedModel):
    """ Order order: ;)
    1. create order (this is implicit even)
    2. place/confirm order (make it definitive for payment)
    3. pay/finalize order
    4. collect order
    """

    class Meta:
        verbose_name = "Bestelling"
        verbose_name_plural = "Bestellingen"

    objects = OrderManager()

    products = models.ManyToManyField("Product", through="OrderProduct")
    order_round = models.ForeignKey("OrderRound", related_name="orders")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="orders")

    # If order has been paid
    finalized = models.BooleanField(default=False)
    # Whether the order has been retrieved by the user
    collected = models.BooleanField(default=False)

    debit = models.OneToOneField(Balance, null=True, blank=True)

    def __unicode__(self):
        return "Order %d; value: E%s; user: %s" % (self.id, self.total_price, self.user)

    @property
    def has_products(self):
        return len(self.orderproducts.all()) > 0

    @property
    def total_price(self):
        product_sum = sum([p.total_price for p in self.orderproducts.all()])
        return product_sum + self.order_round.transaction_costs + self.member_fee

    @property
    def total_price_to_pay_with_balances_taken_into_account(self):
        if self.user.balance.credit() > 0:
            total_price = self.total_price - self.user.balance.credit()
            return total_price if total_price > 0 else 0

        if self.user.balance.debit() > 0:
            return self.total_price + self.user.balance.debit()

        return self.total_price

    @property
    def member_fee(self):
        # Return contribution fee if this is users' first order (unfinished orders not included)
        amount_of_finalized_orders = self.user.orders.\
            filter(finalized=True).\
            exclude(pk=self.pk).\
            exclude(pk__gt=self.pk).\
            count()

        if amount_of_finalized_orders == 0:
            return Decimal(settings.MEMBER_FEE)

        return Decimal(0)

    @property
    def user_order_id(self):
        user_orders = self.user.orders.exclude(orderproducts=None).order_by("pk")
        for index, uo in enumerate(user_orders):
            if uo == self:
                return index + 1

    def _notify_admins_about_new_order(self):
        # This is most likely temporary
        message = "Hoi!\n\nEr is een nieuwe bestelling van gebruiker %s.\n\nBestelling\n\n%s" % \
                  (self.user, "\n".join(["%d x %s (%s)" % (op.amount, op.product.name, op.product.supplier)
                                         for op in self.orderproducts.all()]))

        mail_admins("Bestelling bevestigd (#%d) van %s" % (self.pk, self.user), message,
                    fail_silently=True)

    def create_and_link_debit(self):
        """
        Create debit and save as self.debit one-to-one
        """
        debit = Balance.objects.create(user=self.user,
                                       type="DR",
                                       amount=self.total_price,
                                       notes="Debit van %s voor bestelling #%d" % (self.total_price, self.pk))
        self.debit = debit

    def update_debit(self):
        """
        Update debit amount and note to current order total.
        """
        self.debit.amount = self.total_price
        self.debit.notes = "Debit van %s voor bestelling #%d" % (self.total_price, self.pk)
        self.debit.save()

    def mail_confirmation(self):
        mail_template = get_template_by_id(ORDER_CONFIRM_MAIL_ID)
        rendered_template_vars = render_mail_template(mail_template, user=self.user, order=self)
        mail_user(self.user, *rendered_template_vars)


class OrderProduct(TimeStampedModel):
    class Meta:
        verbose_name = "Productbestelling"
        verbose_name_plural = "Productbestellingen"

    order = models.ForeignKey("Order", related_name="orderproducts")
    product = models.ForeignKey("Product", related_name="orderproducts")
    amount = models.IntegerField(verbose_name="Aantal")

    def __unicode__(self):
        return "%d x %s" % (self.amount, self.product)

    @property
    def total_price(self):
        return self.amount * self.product.retail_price


class OrderProductCorrection(TimeStampedModel):
    class Meta:
        verbose_name = "Productbestelling-correctie"
        verbose_name_plural = "Productbestelling-correcties"

    order_product = models.OneToOneField("OrderProduct", related_name="correction")
    supplied_amount = models.DecimalField(max_digits=6, decimal_places=1)
    notes = models.TextField(blank=True)
    credit = models.OneToOneField(Balance)

    def __unicode__(self):
        return "Correction on OrderProduct: %s" % self.order_product

    def calculate_refund(self):
        before_correction = self.order_product.total_price
        new_price = self.supplied_amount * self.order_product.product.retail_price
        return Decimal(before_correction - new_price).quantize(Decimal('.01'), rounding=ROUND_DOWN)

    def _create_credit(self):
        return Balance.objects.create(user=self.order_product.order.user,
                                      type="CR",
                                      amount=self.calculate_refund(),
                                      notes="Correctie in ronde %d, product %s, geleverd: %s i.p.v. %s" %
                                            (self.order_product.product.order_round.id,
                                             self.order_product.product.name,
                                             self.supplied_amount,
                                             self.order_product.amount))

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.credit = self._create_credit()
        super(OrderProductCorrection, self).save(*args, **kwargs)


class Product(TimeStampedModel):
    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Producten"

    UNITS = (
        ('Stuk', 'Stuk'),
        ('Gram',  'Gram'),
        ('Decagram', 'Decagram (10g)'),
        ('Hectogram', 'Hectogram (100g)'),
        ('Half pond', 'Half pond (250g)'),
        ('Pond',  'Pond (500g)'),
        ('Kilogram', 'Kilogram'),
        ('Deciliter', 'Deciliter (100ml)'),
        ('Liter',  'Liter'),
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    unit_of_measurement = models.CharField(max_length=10, choices=UNITS)
    base_price = models.DecimalField(max_digits=6, decimal_places=2)
    supplier = models.ForeignKey("Supplier", related_name="products")
    order_round = models.ForeignKey("OrderRound", related_name="products")

    minimum_total_order = models.IntegerField(null=True, blank=True)
    maximum_total_order = models.IntegerField(null=True, blank=True)

    def __unicode__(self):
        return '[ronde %s] %s (%s)' % (self.order_round.pk, self.name, self.supplier)

    @property
    def retail_price(self):
        total_percentage = 100 + self.order_round.markup_percentage
        new_price = (self.base_price / 100) * total_percentage
        rounded = new_price.quantize(Decimal('.01'), rounding=ROUND_UP)
        return rounded

    @property
    def amount_available(self):
        if self.maximum_total_order is None:
            return
        maximum = self.maximum_total_order
        total = self.amount_ordered
        return maximum - total

    @property
    def amount_ordered(self):
        orderproducts = self.orderproducts.filter(order__finalized=True)
        total = sum(op.amount for op in orderproducts)
        return total

    @property
    def percentage_available_of_max(self):
        if self.maximum_total_order is None:
            return 100
        return int((float(self.amount_available) / float(self.maximum_total_order)) * 100)

    @property
    def is_available(self):
        if self.maximum_total_order is None:
            return True
        return self.amount_available > 0

    def create_corrections(self):
        for order_product in self.orderproducts.filter(correction__isnull=True):
            OrderProductCorrection.objects.create(
                order_product=order_product,
                supplied_amount=0,
                notes='Product niet geleverd: "%s" (%s) [%s]' % (self.name, self.supplier.name, self.id)
            )
