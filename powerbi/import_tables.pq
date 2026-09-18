// Save as a function query named LoadOlist. OutputFolder is a text parameter.
(TableName as text) as table =>
let
    Source = Csv.Document(File.Contents(OutputFolder & TableName & ".csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Names = Table.ColumnNames(Headers),
    Dates = List.Intersect({Names, {"purchase_date","first_purchase_date","date"}}),
    Timestamps = List.Intersect({Names, {"order_purchase_timestamp","order_approved_at",
        "order_delivered_carrier_date","order_delivered_customer_date","order_estimated_delivery_date","shipping_limit_date"}}),
    Money = List.Intersect({Names, {"price","freight_value","merchandise_value","payment_value","payment_difference"}}),
    Integers = List.Intersect({Names, {"number_of_items","seller_count","payment_type_count","payment_record_count",
        "installment_count","customer_order_number","order_item_id","review_score","delay_days",
        "year","quarter","month_number","week","weekday_number"}}),
    Flags = List.Intersect({Names, {"commercial_eligible","delivery_eligible","review_eligible","is_late","low_review",
        "is_returning","is_canceled","is_unavailable","has_items","has_payments","has_review","invalid_chronology","is_weekend"}}),
    Nulls = Table.ReplaceValue(Headers,"",null,Replacer.ReplaceValue,Names),
    Types = List.Combine({List.Transform(Dates,each {_,type date}),List.Transform(Timestamps,each {_,type datetime}),
        List.Transform(Money,each {_,Currency.Type}),List.Transform(Integers,each {_,Int64.Type}),
        List.Transform(List.Intersect({Names,{"delivery_days"}}),each {_,type number})}),
    Typed = Table.TransformColumnTypes(Nulls, Types, "en-US"),
    Booleans = Table.TransformColumns(Typed,List.Transform(Flags,each {_, (v) => if v=null then null else Text.Lower(Text.From(v))="true", type nullable logical}))
in Booleans
