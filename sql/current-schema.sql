-- Current Sulong-NIR schema snapshot (SQLite).
-- Schema only: no application data is included.
-- Generated from the configured database after applying Django migrations.
-- Django app migrations remain the authoritative schema history.
PRAGMA foreign_keys = ON;

CREATE TABLE "alert_delivery" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "channel" varchar(10) NOT NULL, "status" varchar(10) NOT NULL, "external_id" varchar(100) NOT NULL, "error_message" text NOT NULL, "sent_at" datetime NULL, "delivered_at" datetime NULL, "read_at" datetime NULL, "created_at" datetime NOT NULL, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "alert_id" bigint NOT NULL REFERENCES "emergency_alert" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "delivery_unique_per_channel" UNIQUE ("alert_id", "user_id", "channel"));

CREATE TABLE "alert_template" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL UNIQUE, "subject_template" varchar(200) NOT NULL, "message_template" text NOT NULL, "default_severity" varchar(15) NOT NULL, "default_channels" text NOT NULL CHECK ((JSON_VALID("default_channels") OR "default_channels" IS NULL)), "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);

CREATE TABLE "alerts_alertpreference" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "receive_in_app" bool NOT NULL, "receive_email" bool NOT NULL, "receive_sms" bool NOT NULL, "receive_push" bool NOT NULL, "min_severity" varchar(15) NOT NULL, "quiet_hours_start" time NULL, "quiet_hours_end" time NULL, "updated_at" datetime NOT NULL, "user_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "auth_group" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(150) NOT NULL UNIQUE);

CREATE TABLE "auth_group_permissions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED, "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "auth_permission" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "content_type_id" integer NOT NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "codename" varchar(100) NOT NULL, "name" varchar(255) NOT NULL);

CREATE TABLE "auth_user" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "password" varchar(128) NOT NULL, "last_login" datetime NULL, "is_superuser" bool NOT NULL, "username" varchar(150) NOT NULL UNIQUE, "last_name" varchar(150) NOT NULL, "email" varchar(254) NOT NULL, "is_staff" bool NOT NULL, "is_active" bool NOT NULL, "date_joined" datetime NOT NULL, "first_name" varchar(150) NOT NULL);

CREATE TABLE "auth_user_groups" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "auth_user_user_permissions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "concern_category" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "description" text NOT NULL, "is_active" bool NOT NULL, "sort_order" smallint unsigned NOT NULL CHECK ("sort_order" >= 0), "parent_id" bigint NULL REFERENCES "concern_category" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "concern_category_parent_name_uniq" UNIQUE ("parent_id", "name"));

CREATE TABLE "concern_report" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "reference" char(32) NOT NULL UNIQUE, "subject" varchar(200) NOT NULL, "description" text NOT NULL, "priority" varchar(10) NOT NULL, "status" varchar(24) NOT NULL, "location_details" varchar(255) NOT NULL, "latitude" decimal NULL, "longitude" decimal NULL, "submitted_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "due_at" datetime NULL, "resolved_at" datetime NULL, "assigned_to_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "category_id" bigint NOT NULL REFERENCES "concern_category" ("id") DEFERRABLE INITIALLY DEFERRED, "department_id" bigint NULL REFERENCES "tbldepartment" ("id") DEFERRABLE INITIALLY DEFERRED, "reporter_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "area_id" bigint NOT NULL REFERENCES "geographic_area" ("id") DEFERRABLE INITIALLY DEFERRED, "ai_analyzed_at" datetime NULL, "ai_category" varchar(120) NOT NULL, "ai_confidence" real NULL, "ai_duplicate_score" real NULL, "ai_subcategory" varchar(120) NOT NULL, "ai_duplicate_of_id" bigint NULL REFERENCES "concern_report" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "concern_coordinates_together" CHECK ((("latitude" IS NULL AND "longitude" IS NULL) OR ("latitude" IS NOT NULL AND "longitude" IS NOT NULL))));

CREATE TABLE "django_admin_log" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "object_id" text NULL, "object_repr" varchar(200) NOT NULL, "action_flag" smallint unsigned NOT NULL CHECK ("action_flag" >= 0), "change_message" text NOT NULL, "content_type_id" integer NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "action_time" datetime NOT NULL);

CREATE TABLE "django_content_type" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "app_label" varchar(100) NOT NULL, "model" varchar(100) NOT NULL);

CREATE TABLE "django_migrations" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "app" varchar(255) NOT NULL, "name" varchar(255) NOT NULL, "applied" datetime NOT NULL);

CREATE TABLE "django_session" ("session_key" varchar(40) NOT NULL PRIMARY KEY, "session_data" text NOT NULL, "expire_date" datetime NOT NULL);

CREATE TABLE "emergency_alert" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "reference" char(32) NOT NULL UNIQUE, "title" varchar(200) NOT NULL, "message" text NOT NULL, "severity" varchar(15) NOT NULL, "scope" varchar(20) NOT NULL, "channels" text NOT NULL CHECK ((JSON_VALID("channels") OR "channels" IS NULL)), "sent_at" datetime NULL, "expires_at" datetime NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "emergency_alert_target_areas" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "emergencyalert_id" bigint NOT NULL REFERENCES "emergency_alert" ("id") DEFERRABLE INITIALLY DEFERRED, "geographicarea_id" bigint NOT NULL REFERENCES "geographic_area" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "emergency_alert_target_users" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "emergencyalert_id" bigint NOT NULL REFERENCES "emergency_alert" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "geographic_area" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "level" varchar(20) NOT NULL, "name" varchar(120) NOT NULL, "code" varchar(30) NOT NULL, "is_active" bool NOT NULL, "parent_id" bigint NULL REFERENCES "geographic_area" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "concern_area_parent_name_uniq" UNIQUE ("parent_id", "name"));

CREATE TABLE "report_assignment_history" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "note" text NOT NULL, "assigned_at" datetime NOT NULL, "ended_at" datetime NULL, "assigned_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "assignee_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "department_id" bigint NULL REFERENCES "tbldepartment" ("id") DEFERRABLE INITIALLY DEFERRED, "report_id" bigint NOT NULL REFERENCES "concern_report" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "report_attachment" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "file" varchar(100) NOT NULL, "original_name" varchar(255) NOT NULL, "content_type" varchar(100) NOT NULL, "size_bytes" bigint unsigned NOT NULL CHECK ("size_bytes" >= 0), "uploaded_at" datetime NOT NULL, "report_id" bigint NOT NULL REFERENCES "concern_report" ("id") DEFERRABLE INITIALLY DEFERRED, "uploaded_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "report_status_history" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "old_status" varchar(24) NOT NULL, "new_status" varchar(24) NOT NULL, "comment" text NOT NULL, "visibility" varchar(10) NOT NULL, "created_at" datetime NOT NULL, "actor_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "report_id" bigint NOT NULL REFERENCES "concern_report" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "service" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "reference" char(32) NOT NULL UNIQUE, "name" varchar(200) NOT NULL, "slug" varchar(220) NOT NULL UNIQUE, "description" text NOT NULL, "address" text NOT NULL, "latitude" decimal NULL, "longitude" decimal NULL, "phone" varchar(50) NOT NULL, "email" varchar(254) NOT NULL, "website" varchar(200) NOT NULL, "hours_monday" varchar(100) NOT NULL, "hours_tuesday" varchar(100) NOT NULL, "hours_wednesday" varchar(100) NOT NULL, "hours_thursday" varchar(100) NOT NULL, "hours_friday" varchar(100) NOT NULL, "hours_saturday" varchar(100) NOT NULL, "hours_sunday" varchar(100) NOT NULL, "status" varchar(20) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "barangay_id" bigint NULL REFERENCES "geographic_area" ("id") DEFERRABLE INITIALLY DEFERRED, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "category_id" bigint NOT NULL REFERENCES "service_category" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "service_category" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(100) NOT NULL, "description" text NOT NULL, "icon" varchar(50) NOT NULL, "sort_order" smallint unsigned NOT NULL CHECK ("sort_order" >= 0), "is_active" bool NOT NULL, "slug" varchar(220) NOT NULL, "parent_id" bigint NULL REFERENCES "service_category" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "service_category_parent_name_uniq" UNIQUE ("parent_id", "name"));

CREATE TABLE "service_review" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "rating" smallint unsigned NOT NULL CHECK ("rating" >= 0), "comment" text NOT NULL, "created_at" datetime NOT NULL, "service_id" bigint NOT NULL REFERENCES "service" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "service_review_unique" UNIQUE ("service_id", "user_id"));

CREATE TABLE "tbldepartment" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "code" varchar(20) NOT NULL UNIQUE, "name" varchar(100) NOT NULL UNIQUE, "description" text NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);

CREATE TABLE "tblinfo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(255) NOT NULL, "age" integer unsigned NOT NULL CHECK ("age" >= 0), "address" varchar(255) NOT NULL, "email" varchar(255) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "user_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "tblrequestupdate" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "comment" text NOT NULL, "previous_status" varchar(20) NOT NULL, "new_status" varchar(20) NOT NULL, "created_at" datetime NOT NULL, "author_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "request_id" bigint NOT NULL REFERENCES "tblservicerequest" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "tblservicerequest" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "reference" char(32) NOT NULL UNIQUE, "subject" varchar(200) NOT NULL, "description" text NOT NULL, "request_type" varchar(20) NOT NULL, "priority" varchar(10) NOT NULL, "status" varchar(20) NOT NULL, "submitted_at" datetime NOT NULL, "due_at" datetime NULL, "resolved_at" datetime NULL, "updated_at" datetime NOT NULL, "assigned_to_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "department_id" bigint NULL REFERENCES "tbldepartment" ("id") DEFERRABLE INITIALLY DEFERRED, "requester_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "tbluserprofile" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "employee_id" varchar(50) NULL UNIQUE, "phone_number" varchar(20) NOT NULL, "role" varchar(20) NOT NULL, "status" varchar(20) NOT NULL, "bio" text NOT NULL, "avatar_url" varchar(200) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "department_id" bigint NULL REFERENCES "tbldepartment" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "transit_agency" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "short_name" varchar(50) NOT NULL, "description" text NOT NULL, "website" varchar(200) NOT NULL, "phone" varchar(50) NOT NULL, "email" varchar(254) NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);

CREATE TABLE "transit_alert" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(200) NOT NULL, "message" text NOT NULL, "severity" varchar(10) NOT NULL, "starts_at" datetime NOT NULL, "ends_at" datetime NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "agency_id" bigint NOT NULL REFERENCES "transit_agency" ("id") DEFERRABLE INITIALLY DEFERRED, "created_by_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "route_id" bigint NULL REFERENCES "transit_route" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "transit_route" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "short_name" varchar(50) NOT NULL, "long_name" varchar(200) NOT NULL, "description" text NOT NULL, "vehicle_type" varchar(20) NOT NULL, "color" varchar(7) NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "agency_id" bigint NOT NULL REFERENCES "transit_agency" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "transit_schedule" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "day_of_week" integer NOT NULL, "departure_time" time NOT NULL, "estimated_duration_minutes" smallint unsigned NOT NULL CHECK ("estimated_duration_minutes" >= 0), "frequency_minutes" smallint unsigned NULL CHECK ("frequency_minutes" >= 0), "is_active" bool NOT NULL, "valid_from" date NULL, "valid_until" date NULL, "route_id" bigint NOT NULL REFERENCES "transit_route" ("id") DEFERRABLE INITIALLY DEFERRED, "destination_stop_id" bigint NOT NULL REFERENCES "transit_stop" ("id") DEFERRABLE INITIALLY DEFERRED, "origin_stop_id" bigint NOT NULL REFERENCES "transit_stop" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "transit_schedule_unique" UNIQUE ("route_id", "day_of_week", "departure_time", "origin_stop_id"));

CREATE TABLE "transit_stop" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(200) NOT NULL, "latitude" decimal NOT NULL, "longitude" decimal NOT NULL, "sequence" smallint unsigned NOT NULL CHECK ("sequence" >= 0), "stop_type" varchar(20) NOT NULL, "estimated_time_minutes" smallint unsigned NULL CHECK ("estimated_time_minutes" >= 0), "landmarks" text NOT NULL, "is_active" bool NOT NULL, "route_id" bigint NOT NULL REFERENCES "transit_route" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "transit_stop_route_seq_uniq" UNIQUE ("route_id", "sequence"));

CREATE INDEX "alert_active_sev_idx" ON "emergency_alert" ("is_active", "severity", "created_at");

CREATE INDEX "alert_delivery_alert_id_6cdfb427" ON "alert_delivery" ("alert_id");

CREATE INDEX "alert_delivery_user_id_81c6f613" ON "alert_delivery" ("user_id");

CREATE INDEX "alert_sent_exp_idx" ON "emergency_alert" ("sent_at", "expires_at");

CREATE INDEX "auth_group_permissions_group_id_b120cbf9" ON "auth_group_permissions" ("group_id");

CREATE UNIQUE INDEX "auth_group_permissions_group_id_permission_id_0cd325b0_uniq" ON "auth_group_permissions" ("group_id", "permission_id");

CREATE INDEX "auth_group_permissions_permission_id_84c5c92e" ON "auth_group_permissions" ("permission_id");

CREATE INDEX "auth_permission_content_type_id_2f476e4b" ON "auth_permission" ("content_type_id");

CREATE UNIQUE INDEX "auth_permission_content_type_id_codename_01ab375a_uniq" ON "auth_permission" ("content_type_id", "codename");

CREATE INDEX "auth_user_groups_group_id_97559544" ON "auth_user_groups" ("group_id");

CREATE INDEX "auth_user_groups_user_id_6a12ed8b" ON "auth_user_groups" ("user_id");

CREATE UNIQUE INDEX "auth_user_groups_user_id_group_id_94350c0c_uniq" ON "auth_user_groups" ("user_id", "group_id");

CREATE INDEX "auth_user_user_permissions_permission_id_1fbb5f2c" ON "auth_user_user_permissions" ("permission_id");

CREATE INDEX "auth_user_user_permissions_user_id_a95ead1b" ON "auth_user_user_permissions" ("user_id");

CREATE UNIQUE INDEX "auth_user_user_permissions_user_id_permission_id_14a6b632_uniq" ON "auth_user_user_permissions" ("user_id", "permission_id");

CREATE INDEX "concern_area_status_idx" ON "concern_report" ("area_id", "status", "submitted_at");

CREATE INDEX "concern_assign_date_idx" ON "report_assignment_history" ("report_id", "assigned_at");

CREATE INDEX "concern_assignee_status_idx" ON "concern_report" ("assigned_to_id", "status");

CREATE INDEX "concern_attach_date_idx" ON "report_attachment" ("report_id", "uploaded_at");

CREATE INDEX "concern_category_parent_id_e81004b0" ON "concern_category" ("parent_id");

CREATE INDEX "concern_dept_status_idx" ON "concern_report" ("department_id", "status", "submitted_at");

CREATE INDEX "concern_history_date_idx" ON "report_status_history" ("report_id", "created_at");

CREATE UNIQUE INDEX "concern_one_active_assignment" ON "report_assignment_history" ("report_id") WHERE "ended_at" IS NULL;

CREATE INDEX "concern_report_ai_duplicate_of_id_88967883" ON "concern_report" ("ai_duplicate_of_id");

CREATE INDEX "concern_report_area_id_b825fde8" ON "concern_report" ("area_id");

CREATE INDEX "concern_report_assigned_to_id_0a7b96db" ON "concern_report" ("assigned_to_id");

CREATE INDEX "concern_report_category_id_3ee4361f" ON "concern_report" ("category_id");

CREATE INDEX "concern_report_department_id_3d4892db" ON "concern_report" ("department_id");

CREATE INDEX "concern_report_reporter_id_7c009429" ON "concern_report" ("reporter_id");

CREATE INDEX "concern_reporter_date_idx" ON "concern_report" ("reporter_id", "submitted_at");

CREATE INDEX "concern_status_priority_idx" ON "concern_report" ("status", "priority", "submitted_at");

CREATE INDEX "delivery_alert_user_ch_idx" ON "alert_delivery" ("alert_id", "user_id", "channel");

CREATE INDEX "delivery_status_idx" ON "alert_delivery" ("status", "created_at");

CREATE INDEX "django_admin_log_content_type_id_c4bce8eb" ON "django_admin_log" ("content_type_id");

CREATE INDEX "django_admin_log_user_id_c564eba6" ON "django_admin_log" ("user_id");

CREATE UNIQUE INDEX "django_content_type_app_label_model_76bd3d3b_uniq" ON "django_content_type" ("app_label", "model");

CREATE INDEX "django_session_expire_date_a5c62663" ON "django_session" ("expire_date");

CREATE INDEX "emergency_alert_created_by_id_db1d7631" ON "emergency_alert" ("created_by_id");

CREATE INDEX "emergency_alert_target_areas_emergencyalert_id_0d8ebe55" ON "emergency_alert_target_areas" ("emergencyalert_id");

CREATE UNIQUE INDEX "emergency_alert_target_areas_emergencyalert_id_geographicarea_id_03eaf363_uniq" ON "emergency_alert_target_areas" ("emergencyalert_id", "geographicarea_id");

CREATE INDEX "emergency_alert_target_areas_geographicarea_id_86079dbf" ON "emergency_alert_target_areas" ("geographicarea_id");

CREATE INDEX "emergency_alert_target_users_emergencyalert_id_f75769ea" ON "emergency_alert_target_users" ("emergencyalert_id");

CREATE UNIQUE INDEX "emergency_alert_target_users_emergencyalert_id_user_id_366ccf01_uniq" ON "emergency_alert_target_users" ("emergencyalert_id", "user_id");

CREATE INDEX "emergency_alert_target_users_user_id_90194823" ON "emergency_alert_target_users" ("user_id");

CREATE INDEX "geographic_area_parent_id_bd3761b6" ON "geographic_area" ("parent_id");

CREATE INDEX "report_assignment_history_assigned_by_id_9ee1245c" ON "report_assignment_history" ("assigned_by_id");

CREATE INDEX "report_assignment_history_assignee_id_d2410ee9" ON "report_assignment_history" ("assignee_id");

CREATE INDEX "report_assignment_history_department_id_bac55448" ON "report_assignment_history" ("department_id");

CREATE INDEX "report_assignment_history_report_id_25d79a56" ON "report_assignment_history" ("report_id");

CREATE INDEX "report_attachment_report_id_08eed81b" ON "report_attachment" ("report_id");

CREATE INDEX "report_attachment_uploaded_by_id_73aca335" ON "report_attachment" ("uploaded_by_id");

CREATE INDEX "report_status_history_actor_id_f6382767" ON "report_status_history" ("actor_id");

CREATE INDEX "report_status_history_report_id_abe9e431" ON "report_status_history" ("report_id");

CREATE INDEX "service_barangay_id_3765f34e" ON "service" ("barangay_id");

CREATE INDEX "service_category_id_033f6804" ON "service" ("category_id");

CREATE INDEX "service_category_parent_id_1d45338c" ON "service_category" ("parent_id");

CREATE INDEX "service_category_slug_a2265e93" ON "service_category" ("slug");

CREATE INDEX "service_created_by_id_f40cfa0a" ON "service" ("created_by_id");

CREATE INDEX "service_review_service_id_ac69cbe7" ON "service_review" ("service_id");

CREATE INDEX "service_review_user_id_a7d25629" ON "service_review" ("user_id");

CREATE INDEX "sr_assignee_status_idx" ON "tblservicerequest" ("assigned_to_id", "status");

CREATE INDEX "sr_requester_status_idx" ON "tblservicerequest" ("requester_id", "status");

CREATE INDEX "sr_status_priority_idx" ON "tblservicerequest" ("status", "priority");

CREATE INDEX "svc_brgy_status_idx" ON "service" ("barangay_id", "status");

CREATE INDEX "svc_cat_status_idx" ON "service" ("category_id", "status");

CREATE INDEX "tblinfo_user_id_4a36749d" ON "tblinfo" ("user_id");

CREATE INDEX "tblrequestupdate_author_id_fe9d620d" ON "tblrequestupdate" ("author_id");

CREATE INDEX "tblrequestupdate_request_id_bb43476c" ON "tblrequestupdate" ("request_id");

CREATE INDEX "tblservicerequest_assigned_to_id_84c1ee23" ON "tblservicerequest" ("assigned_to_id");

CREATE INDEX "tblservicerequest_department_id_e5b25ee0" ON "tblservicerequest" ("department_id");

CREATE INDEX "tblservicerequest_requester_id_da639ef1" ON "tblservicerequest" ("requester_id");

CREATE INDEX "tbluserprofile_department_id_9ed12874" ON "tbluserprofile" ("department_id");

CREATE INDEX "transit_alert_agency_id_19e04d5d" ON "transit_alert" ("agency_id");

CREATE INDEX "transit_alert_created_by_id_402bea1d" ON "transit_alert" ("created_by_id");

CREATE INDEX "transit_alert_route_id_f9293972" ON "transit_alert" ("route_id");

CREATE INDEX "transit_route_agency_id_2bb7b9f1" ON "transit_route" ("agency_id");

CREATE INDEX "transit_schedule_destination_stop_id_05f3e712" ON "transit_schedule" ("destination_stop_id");

CREATE INDEX "transit_schedule_origin_stop_id_211c038e" ON "transit_schedule" ("origin_stop_id");

CREATE INDEX "transit_schedule_route_id_432511a9" ON "transit_schedule" ("route_id");

CREATE INDEX "transit_stop_route_id_7347ef5a" ON "transit_stop" ("route_id");
