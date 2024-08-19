/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ndax_lvl1_data` (
  `timestamp_ms` bigint(20) NOT NULL,
  `tkr_id` int(11) NOT NULL,
  `tkr` char(8) DEFAULT NULL,
  `best_bid` decimal(7,2) DEFAULT NULL,
  `best_ask` decimal(7,2) DEFAULT NULL,
  `last_trade_price` decimal(7,2) DEFAULT NULL,
  `last_trade_qty` decimal(6,6) DEFAULT NULL,
  `last_trade_time` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`tkr_id`,`timestamp_ms`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ndax_tkr_data` (
  `timestamp_ms` bigint(20) NOT NULL,
  `tkr_id` int(11) NOT NULL,
  `tkr` char(8) DEFAULT NULL,
  `high` decimal(7,2) DEFAULT NULL,
  `low` decimal(7,2) DEFAULT NULL,
  `open` decimal(7,2) DEFAULT NULL,
  `close` decimal(7,2) DEFAULT NULL,
  `volume` decimal(6,6) DEFAULT NULL,
  `inside_bid_price` decimal(7,2) DEFAULT NULL,
  `inside_ask_price` decimal(7,2) DEFAULT NULL,
  `timestamp_beg_ms` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`tkr_id`,`timestamp_ms`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `paper_trade_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `timestamp_ms` bigint(200) DEFAULT NULL,
  `tkr_id` int(11) DEFAULT NULL,
  `price` decimal(7,2) DEFAULT NULL,
  `fee` decimal(7,2) DEFAULT NULL,
  `action` enum('buy','sell') DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
