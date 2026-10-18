// Canonical CSV queries. Create SourceFolder parameter, then one query per table.
// SourceFolder = "C:\Users\MINH\vinai\Build phase\data\processed"

// dim_annotators
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\dim_annotators.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"annotator_id", type text}, {"full_name", type text}, {"username", type text}, {"role", type text}, {"joined_date", type date}}, "en-US")
in Typed

// dim_reviewers
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\dim_reviewers.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"reviewer_id", type text}, {"full_name", type text}}, "en-US")
in Typed

// dim_tasks_batches
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\dim_tasks_batches.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"task_id", Int64.Type}, {"batch_id", type text}, {"task_name", type text}, {"total_frames_target", Int64.Type}}, "en-US")
in Typed

// dim_classes_labels
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\dim_classes_labels.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"label_key", type text}, {"label_id", Int64.Type}, {"task_id", Int64.Type}, {"label_name", type text}, {"color_hex", type text}}, "en-US")
in Typed

// dim_date
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\dim_date.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"date_key", type date}, {"year", Int64.Type}, {"month_num", Int64.Type}, {"month_name", type text}, {"day_name", type text}, {"week_num", Int64.Type}}, "en-US")
in Typed

// dim_jobs
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\dim_jobs.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"job_id", Int64.Type}, {"task_id", Int64.Type}, {"annotator_id", type text}, {"stage", type text}, {"state", type text}, {"frame_count", Int64.Type}}, "en-US")
in Typed

// fact_job_sessions
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\fact_job_sessions.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"job_id", Int64.Type}, {"task_id", Int64.Type}, {"annotator_id", type text}, {"date_key", type date}, {"status", type text}, {"total_frames", Int64.Type}, {"total_objects", Int64.Type}, {"active_time_hours", type number}}, "en-US")
in Typed

// fact_annotations
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\fact_annotations.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"annotation_id", type text}, {"job_id", Int64.Type}, {"label_key", type text}, {"frame_idx", Int64.Type}, {"shape_type", type text}, {"area_pixels", type number}, {"frame_area_pct", type number}, {"size_scale", type text}}, "en-US")
in Typed

// fact_qa_reviews
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\fact_qa_reviews.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"review_id", type text}, {"job_id", Int64.Type}, {"reviewer_id", type text}, {"review_iteration", Int64.Type}, {"review_decision", type text}, {"reviewed_at", type text}}, "en-US")
in Typed

// fact_qa_defects
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\fact_qa_defects.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"defect_id", type text}, {"review_id", type text}, {"job_id", Int64.Type}, {"label_key", type text}, {"frame_idx", Int64.Type}, {"defect_type", type text}, {"severity", type text}, {"cvat_deep_link", type text}}, "en-US")
in Typed

// fact_ground_truth_eval
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\fact_ground_truth_eval.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"eval_id", type text}, {"job_id", Int64.Type}, {"mean_iou", type number}, {"precision", type number}, {"recall", type number}, {"f1_score", type number}, {"evaluated_at", type text}}, "en-US")
in Typed

// fact_edge_cases
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\fact_edge_cases.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"case_id", type text}, {"number", Int64.Type}, {"task_id", Int64.Type}, {"job_id", Int64.Type}, {"title", type text}, {"description", type text}, {"labels", type text}, {"state", type text}, {"severity", type text}, {"frame", Int64.Type}, {"link_status", type text}, {"cvat_deep_link", type text}, {"source_url", type text}}, "en-US")
in Typed

// report_status
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\report_status.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"task_id", Int64.Type}, {"as_of", type date}, {"is_demo", Int64.Type}, {"source_snapshot", type text}, {"reviews_available", Int64.Type}, {"defects_available", Int64.Type}, {"hours_available", Int64.Type}, {"annotations_available", Int64.Type}, {"gt_available", Int64.Type}, {"warnings", type text}}, "en-US")
in Typed

// kpi_reconciliation
let
    Pointer = Json.Document(File.Contents(SourceFolder & "\current.json")),
    Bundle = SourceFolder & "\" & Text.Replace(Pointer[relative_folder], "/", "\"),
    Source = Csv.Document(File.Contents(Bundle & "\kpi_reconciliation.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"metric", type text}, {"expected_value", type number}, {"unit", type text}}, "en-US")
in Typed
