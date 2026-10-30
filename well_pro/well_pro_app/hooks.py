scheduler_events = {
    "daily": [
        "well_pro.well_pro_app.tasks.run_nightly_wellbeing_scoring"
    ]
}
doc_events = {
	"Health Daily Record": {
		"on_update": "well_pro.well_pro_app.services.scoring.service.on_doctype_update",
		"on_trash": "well_pro.well_pro_app.services.scoring.service.on_doctype_trash",
	},
	"Health Activity": {
		"on_update": "well_pro.well_pro_app.services.scoring.service.on_doctype_update",
		"on_trash": "well_pro.well_pro_app.services.scoring.service.on_doctype_trash",
	},
	"Financial Transaction": {
		"on_update": "well_pro.well_pro_app.services.scoring.service.on_doctype_update",
		"on_trash": "well_pro.well_pro_app.services.scoring.service.on_doctype_trash",
	},
	"Financial Snapshot": {
		"on_update": "well_pro.well_pro_app.services.scoring.service.on_doctype_update",
		"on_trash": "well_pro.well_pro_app.services.scoring.service.on_doctype_trash",
	},
	"Social Activity": {
		"on_update": "well_pro.well_pro_app.services.scoring.service.on_doctype_update",
		"on_trash": "well_pro.well_pro_app.services.scoring.service.on_doctype_trash",
	},
	"Subjective Wellbeing Checkin": {
		"on_update": "well_pro.well_pro_app.services.scoring.service.on_doctype_update",
		"on_trash": "well_pro.well_pro_app.services.scoring.service.on_doctype_trash",
	},
}
