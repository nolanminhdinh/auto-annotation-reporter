// ==============================================================================
// POWER QUERY (M) SCRIPTS CHO BÁO CÁO POWER BI (AUTO-ANNOTATION-REPORTER)
// ==============================================================================
// Hướng dẫn sử dụng:
// 1. Mở Power BI Desktop -> Home -> Transform Data (Power Query Editor).
// 2. Tạo Parameter: "Home" -> "Manage Parameters" -> "New Parameter"
//    - Name: SourceFolder
//    - Type: Text
//    - Current Value: "C:\Users\MINH\vinai\Build phase\powerbi\data"
// 3. Với mỗi truy vấn bên dưới: "New Source" -> "Blank Query" -> "Advanced Editor",
//    dán mã tương ứng và đổi tên Query khớp với tên bảng.
// ==============================================================================

// ------------------------------------------------------------------------------
// PARAMETER: SourceFolder
// ------------------------------------------------------------------------------
"C:\Users\MINH\vinai\Build phase\powerbi\data" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

// ------------------------------------------------------------------------------
// 1. dim_annotators
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\dim_annotators.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"annotator_id", Int64.Type}, 
        {"full_name", type text}, 
        {"username", type text}, 
        {"role", type text}, 
        {"joined_date", type date}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// 2. dim_reviewers
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\dim_reviewers.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"reviewer_id", Int64.Type}, 
        {"full_name", type text}, 
        {"role", type text}, 
        {"team", type text}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// 3. dim_tasks_batches
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\dim_tasks_batches.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"task_id", Int64.Type}, 
        {"task_name", type text}, 
        {"batch_id", type text}, 
        {"total_frames_target", Int64.Type}, 
        {"target_deadline", type date}, 
        {"status", type text}, 
        {"description", type text}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// 4. dim_classes_labels
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\dim_classes_labels.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"label_id", Int64.Type}, 
        {"label_name", type text}, 
        {"label_category", type text}, 
        {"color_hex", type text}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// 5. dim_date
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\dim_date.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"date_key", type date}, 
        {"day", Int64.Type}, 
        {"day_name", type text}, 
        {"week_num", Int64.Type}, 
        {"month_num", Int64.Type}, 
        {"month_name", type text}, 
        {"quarter", type text}, 
        {"year", Int64.Type}, 
        {"is_weekend", Int64.Type}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// 6. dim_jobs
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\dim_jobs.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"job_id", Int64.Type}, 
        {"task_id", Int64.Type}, 
        {"annotator_id", Int64.Type}, 
        {"stage", type text}, 
        {"state", type text}, 
        {"status", type text}, 
        {"type", type text}, 
        {"frame_count", Int64.Type}, 
        {"updated_date", type date}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// 7. fact_job_sessions
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\fact_job_sessions.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"job_id", Int64.Type}, 
        {"task_id", Int64.Type}, 
        {"annotator_id", Int64.Type}, 
        {"date_key", type date}, 
        {"total_frames", Int64.Type}, 
        {"total_objects", Int64.Type}, 
        {"active_time_hours", type number}, 
        {"status", type text}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// 8. fact_annotations
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\fact_annotations.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"annotation_id", type text}, 
        {"job_id", Int64.Type}, 
        {"frame_idx", Int64.Type}, 
        {"label_id", Int64.Type}, 
        {"shape_type", type text}, 
        {"bbox_width", type number}, 
        {"bbox_height", type number}, 
        {"area_pixels", type number}, 
        {"frame_area_pct", type number}, 
        {"size_scale", type text}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// 9. fact_qa_reviews
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\fact_qa_reviews.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"review_id", type text}, 
        {"job_id", Int64.Type}, 
        {"reviewer_id", Int64.Type}, 
        {"review_iteration", Int64.Type}, 
        {"review_decision", type text}, 
        {"reviewed_at", type datetime}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// 10. fact_qa_defects
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\fact_qa_defects.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"defect_id", type text}, 
        {"review_id", type text}, 
        {"job_id", Int64.Type}, 
        {"frame_idx", Int64.Type}, 
        {"label_id", Int64.Type}, 
        {"defect_type", type text}, 
        {"severity", type text}, 
        {"description", type text}, 
        {"cvat_deep_link", type text}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// 11. fact_ground_truth_eval
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\fact_ground_truth_eval.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"eval_id", type text}, 
        {"job_id", Int64.Type}, 
        {"mean_iou", type number}, 
        {"precision", type number}, 
        {"recall", type number}, 
        {"f1_score", type number}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// 12. fact_edge_cases
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "\fact_edge_cases.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"case_id", type text}, 
        {"number", Int64.Type}, 
        {"title", type text}, 
        {"description", type text}, 
        {"labels", type text}, 
        {"state", type text}, 
        {"author", type text}, 
        {"severity", type text}, 
        {"task_id", Int64.Type}, 
        {"job_id", Int64.Type}, 
        {"frame", Int64.Type}, 
        {"link_status", type text}, 
        {"cvat_deep_link", type text}, 
        {"source_url", type text}
    })
in
    #"Changed Type"
