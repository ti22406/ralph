# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.db import models as db

from lck.django.choices import Choices


class PricingAggregate(Choices):
    """The way to aggregate values of a variable."""

    _ = Choices.Choice

    sum = _("Sum") << {'function': db.Sum}
    average = _("Average") << {'function': db.Avg}
    min = _("Minimum") << {'function': db.Min}
    max = _("Maximum") << {'function': db.Max}


class PricingGroup(db.Model):
    """A group of devices that are priced according to common rules for the given month."""

    name = db.CharField(max_length=64)
    devices = db.ManyToManyField('discovery.Device')
    date = db.DateField()

    class Meta:
        unique_together = 'name', 'date'


class PricingFormula(db.Model):
    """
    A formula for pricing a specific component in a specific pricing group.
    """
    group = db.ForeignKey('discovery.PricingGroup')
    component_group = db.ForeignKey('discovery.ComponentModelGroup')
    formula = db.TextField()

    @staticmethod
    def eval_formula(formula, variables):
        builtins = {
            'sum': sum,
            'max': max,
            'min': min,
        }
        return eval(
            formula,
            {'__builtins__': builtins},
            variables,
        )

    def get_value(self, **kwargs):
        variables = {}
        for variable in self.group.pricingvariable_set.all():
            variables[variable.name] = variable.get_value()
        variables.update(kwargs)
        return PricingFormula.eval_formula(self.formula, variables)

    def get_example(self):
        try:
            return self.get_value(size=1)
        except Exception as e:
            return unicode(e)

    class Meta:
        unique_together = 'group', 'component_group'


class PricingVariable(db.Model):
    """
    A variable that is used in the pricing formulas.
    """
    name = db.CharField(max_length=64)
    group = db.ForeignKey('discovery.PricingGroup')
    aggregate = db.PositiveIntegerField(
        choices=PricingAggregate(),
        default=PricingAggregate.sum.id,
    )

    def get_value(self):
        function = PricingAggregate.FromID(self.aggregate).function
        d = self.pricingvalue_set.aggregate(function('value'))
        return d.values()[0]

    def get_x(self):
        return 'x'

    class Meta:
        unique_together = 'group', 'name'



class PricingValue(db.Model):
    """
    A value of a variable that is used in the pricing formulas.
    """
    device = db.ForeignKey('discovery.Device')
    variable =  db.ForeignKey('discovery.PricingVariable')
    value = db.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = 'device', 'variable'
