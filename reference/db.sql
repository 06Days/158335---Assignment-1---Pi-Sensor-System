BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "EventTypes" (
	"TypeID"	INTEGER NOT NULL,
	"Name"	TEXT,
	"Description"	TEXT,
	PRIMARY KEY("TypeID" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "SensorEvents" (
	"EventID"	INTEGER NOT NULL,
	"TypeID"	INTEGER NOT NULL,
	"RecordID"	INTEGER NOT NULL,
	PRIMARY KEY("EventID" AUTOINCREMENT),
	FOREIGN KEY("RecordID") REFERENCES "SensorRecords"("RecordID"),
	FOREIGN KEY("TypeID") REFERENCES "EventTypes"("TypeID")
);
CREATE TABLE IF NOT EXISTS "SensorRecords" (
	"RecordID"	INTEGER NOT NULL,
	"DateTime"	DateTime NOT NULL,
	"Temperature"	REAL NOT NULL,
	"Pressure"	REAL NOT NULL,
	"Humidity"	REAL NOT NULL,
	PRIMARY KEY("RecordID" AUTOINCREMENT)
);
INSERT INTO "EventTypes" VALUES (1,'Highest Temperature','The highest temperature recorded by the sensor');
INSERT INTO "EventTypes" VALUES (2,'Lowest Temperature','The lowest temperature recorded by the sensor');
INSERT INTO "EventTypes" VALUES (3,'Highest Pressure','The highest air pressure recorded by the sensor');
INSERT INTO "EventTypes" VALUES (4,'Lowest Pressure','The lowest air pressure recorded by the sensor');
INSERT INTO "EventTypes" VALUES (5,'Highest Humidity','The highest humidity recorded by the sensor');
INSERT INTO "EventTypes" VALUES (6,'Lowest Humidity','The lowest humidity recorded by the sensor');
COMMIT;
