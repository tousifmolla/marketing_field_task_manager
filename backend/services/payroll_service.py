from decimal import Decimal

def calculate_net_salary(basic, ta_da=0, overtime=0, sales_incentive=0, other_incentive=0, deductions=0):
    values = map(lambda value: Decimal(str(value or 0)), [basic, ta_da, overtime, sales_incentive, other_incentive, deductions])
    basic, ta_da, overtime, sales, other, deductions = values
    return basic + ta_da + overtime + sales + other - deductions
