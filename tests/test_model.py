"""Small synthetic fixtures test failure modes, never generate portfolio findings."""
import unittest
import pandas as pd
from src.data_processing import build_model
from src.feature_engineering import cohorts

def fixture():
    return {
      'orders':pd.DataFrame([dict(order_id='o1',customer_id='c1',order_status='delivered',
          order_purchase_timestamp='2018-01-01 10:00',order_approved_at='2018-01-01 11:00',
          order_delivered_carrier_date='2018-01-02',order_delivered_customer_date='2018-01-05 18:00',order_estimated_delivery_date='2018-01-05')]),
      'customers':pd.DataFrame([dict(customer_id='c1',customer_unique_id='u1',customer_city='X',customer_state='SP',customer_zip_code_prefix='00001')]),
      'items':pd.DataFrame([dict(order_id='o1',order_item_id=j,product_id='p1',seller_id='s1',shipping_limit_date='2018-01-03',price=price,freight_value=5.) for j,price in [(1,40.),(2,60.)]]),
      'payments':pd.DataFrame([dict(order_id='o1',payment_sequential=j,payment_type='credit_card',payment_installments=1,payment_value=v) for j,v in [(1,70.),(2,40.)]]),
      'products':pd.DataFrame([dict(product_id='p1',product_category_name='cat')]),
      'translation':pd.DataFrame([dict(product_category_name='cat',product_category_name_english='category')]),
      'sellers':pd.DataFrame([dict(seller_id='s1',seller_state='SP')]),
      'reviews':pd.DataFrame([dict(review_id='r1',order_id='o1',review_score=2,review_creation_date='2018-01-06',review_answer_timestamp='2018-01-07'),
                             dict(review_id='r2',order_id='o1',review_score=4,review_creation_date='2018-01-08',review_answer_timestamp='2018-01-09')])}

class GrainTests(unittest.TestCase):
    def test_items_and_payments_do_not_multiply(self):
        m,checks,_,_=build_model(fixture());o=m['FactOrders'].iloc[0]
        self.assertEqual(o.merchandise_value,100)
        self.assertEqual(o.payment_value,110)
        self.assertEqual(o.number_of_items,2)
        self.assertTrue(checks.passed.all())
    def test_same_promised_day_is_not_late_and_latest_review_wins(self):
        m,*_=build_model(fixture());o=m['FactOrders'].iloc[0]
        self.assertFalse(o.is_late);self.assertEqual(o.review_score,4)
    def test_bad_chronology_excluded_not_counted_on_time(self):
        r=fixture();r['orders'].loc[0,'order_delivered_customer_date']='2017-12-31'
        m,*_=build_model(r);o=m['FactOrders'].iloc[0]
        self.assertFalse(o.delivery_eligible);self.assertTrue(pd.isna(o.is_late))
    def test_duplicate_primary_key_fails(self):
        r=fixture();r['orders']=pd.concat([r['orders'],r['orders']])
        with self.assertRaises(ValueError):build_model(r)
    def test_orphan_product_fails(self):
        r=fixture();r['items'].loc[0,'product_id']='absent'
        with self.assertRaises(ValueError):build_model(r)
    def test_unobserved_cohorts_are_not_zero(self):
        f=pd.DataFrame({'commercial_eligible':[True,True],
            'order_purchase_timestamp':pd.to_datetime(['2018-01-01','2018-03-01']),
            'first_purchase_date':pd.to_datetime(['2018-01-01','2018-03-01']),
            'customer_unique_id':['a','b']})
        c=cohorts(f)
        self.assertEqual(c.query("cohort_month=='2018-01' and age_month==1").retention_rate.iloc[0],0)
        self.assertTrue(pd.isna(c.query("cohort_month=='2018-01' and age_month==2").retention_rate.iloc[0]))

if __name__=='__main__':unittest.main()
