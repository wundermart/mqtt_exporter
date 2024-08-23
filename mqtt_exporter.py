def _update_metrics(metrics, msg):
    """For each metric on this topic, apply label renaming if present, and export to prometheus"""
    for metric in metrics:
        labels = {'__topic__': metric['topic'],
                  '__msg_topic__': msg.topic, '__value__': str(msg.payload, 'utf-8')}

        if 'label_configs' in metric:
            # If action 'keep' in label_configs fails, or 'drop' succeeds, the metric is not updated
            if not _apply_label_config(labels, metric['label_configs']):
                continue

        # Attempt to extract and convert the metric value to float, specifically handling "cabinet 1/Cabinet temperature"
        if metric['name'] == "cabinet 1/Cabinet temperature":
            try:
                payload_data = json.loads(labels['__value__'])
                for metric_data in payload_data.get("metrics", []):
                    if metric_data['name'] == "cabinet 1/Cabinet temperature":
                        labels['__value__'] = float(metric_data['value'])
                        break
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                logging.error(f"Failed to parse temperature value: {e}")
                continue
        else:
            try:
                labels['__value__'] = float(labels['__value__'].replace(',', '.'))
            except ValueError:
                logging.debug(f"Conversion of {labels['__value__']} to float not possible, continue with value as is.")

        logging.debug('_update_metrics all labels:')
        logging.debug(labels)

        labels = finalize_labels(labels)

        derived_metric = metric.setdefault('derived_metric',
                                           # Add derived metric for when the message was last received (timestamp in milliseconds)
                                           {
                                               'name': f"{metric['name']}_last_received",
                                               'help': f"Last received message for '{metric['name']}'",
                                               'type': 'gauge'
                                           }
                                           )
        derived_labels = {'topic': metric['topic'],
                          'value': int(round(time.time() * 1000))}

        _export_to_prometheus(metric['name'], metric, labels)

        _export_to_prometheus(
            derived_metric['name'], derived_metric, derived_labels)

        if metric.get('expires'):
            if metric.get('expiration_timer'):
                metric.get('expiration_timer').cancel()
                logging.debug(f"_update_metric Canceled existing timer for {metric.get('name')}")

            metric['expiration_timer'] = threading.Timer(metric.get('expires'), _clear_metric, args=(metric, derived_metric))
            metric['expiration_timer'].start()
            logging.debug(f"_update_metric Set a {metric.get('expires')} second expiration timer for {metric.get('name')}")


